libname ds "<DS_DIR>";
filename score '<SCORE_CODE>';

%let score_input=ds.<SCORE_INPUT>;
%let score_output=ds.<SCORE_OUTPUT>;
%let target=<TARGET>;

options mlogic mprint symbolgen;

%macro calc_confusion_matrix(cutoff=,actual=,predict=,score_table=,out_lib=,append=False);
	proc sql noprint;
		select count(*) into:true_positive from &score_table where &actual = 1 and &predict = '1'; /* 1->1 */
		select count(*) into:false_positive from &score_table where &actual = 0 and &predict = '1'; /* 0->1 */
		select count(*) into:true_negative from &score_table where &actual = 0 and &predict = '0'; /* 0->0 */
		select count(*) into:false_negative from &score_table where &actual = 1 and &predict = '0'; /* 1->0 */
	quit;

	proc sql;
		drop table &out_lib..confusion_matrix;
	quit;
	
	data &out_lib..confusion_matrix;
		length cutoff 8;
		cutoff = &cutoff;
		true_positive = &true_positive;
		false_positive = &false_positive;
		true_negative = &true_negative;
		false_negative = &false_negative;
		total = true_positive+false_positive+true_negative+false_negative;
		actual_positive = true_positive + false_negative;
		actual_negative = false_positive + true_negative;
		predicted_positive = true_positive + false_positive;
		predicted_negative = true_negative + false_negative;
		sensitivity = true_positive/actual_positive;
		pv_plus = true_positive/predicted_positive;
		specificity = true_negative/actual_negative;
		_specificity = 1 - specificity;
		depth = (true_positive+false_positive)/total;
		lift = pv_plus/((true_positive+false_negative)/total);
		output;
	run;

	/*	keep all the calculate result */
	%if &append eq True %then %do;
		%if %sysfunc(exist(&out_lib..total_confusion_matrix)) %then
		%do;
			data &out_lib..total_confusion_matrix;
				set &out_lib..total_confusion_matrix &out_lib..confusion_matrix;
			run;
		%end;
		%else %do;
			data &out_lib..total_confusion_matrix;
				set &out_lib..confusion_matrix;
			run;
		%end;
	%end;

%mend calc_confusion_matrix;

%macro tune_score(cut_off=, score_table=, prob=);
	data &score_table;
		set &score_table;
		if &prob gt &cut_off then
		do;
			predict_&target = '1';
		end;
		else
		do;
			predict_&target = '0';
		end;
	run;
%mend tune_score;

data &score_output;
	set &score_input;
	%inc score;
run;

data ds.score_output_temp;
	set &score_output;
	keep &target em_classification em_eventprobability;
	rename em_classification=predict_&target em_eventprobability=p_positive;
	label predict_&target = "predict_&target" p_positive = "p_positive";
run;

%macro exec;
	filename cm catalog "work.sasmacr.source";
	%do i=0 %to 100;
		%tune_score(cut_off=%sysevalf(&i/100), score_table=ds.score_output_temp, prob=p_positive);
		%calc_confusion_matrix(cutoff=%sysevalf(&i/100), actual=&target, predict=predict_&target, score_table=ds.score_output_temp, out_lib=ds, append=True);
	%end;
%mend exec;

%exec;

/* plot the roc */
axis1 order=(0 to 1 by .2) label=(h=1.5 'Sensitivity') length=4in;
axis2 order=(0 to 1 by .2) label=(h=1.5 '1-Specificity') length=4in;
symbol1 i=join v=none c=black;
symbol2 i=join v=none c=black;

proc gplot data = ds.total_confusion_matrix;
	plot sensitivity*_specificity
	/ overlay vaxis=axis1 haxis=axis2;
	title1 c=darkblue h=1.5 f=swissb "ROC Chart";
run; quit;

proc print data=ds.total_confusion_matrix label;
	var cutoff sensitivity _specificity;
	label cutoff="cut-off" _specificity="1-Specificity" sensitivity="Sensitivity";
run;

proc sql;
	drop table ds.total_confusion_matrix;
quit;

filename cm;
