%macro calc_confusion_matrix(cutoff=,actual=,score_table=,out_lib=,append=False,model_name=);
	proc sql noprint;
		select count(*) into:true_positive from &score_table where &actual = 1 and predict_var = '1'; /* 1->1 */
		select count(*) into:false_positive from &score_table where &actual = 0 and predict_var = '1'; /* 0->1 */
		select count(*) into:true_negative from &score_table where &actual = 0 and predict_var = '0'; /* 0->0 */
		select count(*) into:false_negative from &score_table where &actual = 1 and predict_var = '0'; /* 1->0 */
	quit;

	proc sql;
		drop table &out_lib..confusion_matrix;
	quit;
	
	data &out_lib..confusion_matrix;
		length model $20.;
		length cutoff 8;
		cutoff = &cutoff;
		model = &model_name;
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
		if predicted_positive eq 0 then do;
			pv_plus = 0;
		end;
		else do;
			pv_plus = true_positive/predicted_positive;
		end;
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
			predict_var = '1';
		end;
		else
		do;
			predict_var = '0';
		end;
	run;
%mend tune_score;

%macro precondition(score_code=, event_prob=);
	filename score &score_code;
	data ds.score_output_temp;
		set &score_input;
		%inc score;
	run;
	filename score;

	data ds.score_output_temp;
		length predict_var $8;
		set ds.score_output_temp;
		keep &target &event_prob predict_var;
		rename &event_prob=p_positive;
		label p_positive = "p_positive";
	run;
	
%mend precondition;

%macro exec(name=);
	filename cm catalog "work.sasmacr.source";
	%do i=0 %to 20;
		%tune_score(cut_off=%sysevalf(&i/20), score_table=ds.score_output_temp, prob=p_positive);
		%calc_confusion_matrix(cutoff=%sysevalf(&i/20), actual=&target, score_table=ds.score_output_temp, out_lib=ds, append=True, model_name=&name);
	%end;
%mend exec;

%macro plot;
	/* model numbers */
	proc sql noprint;
		select count(*) into:model_num from (select distinct model from ds.total_confusion_matrix);
	quit;

	/* plot the lift */
	axis1 order=(1 to 6 by .5) label=(h=1.5 'Lift') length=4in;
	axis2 order=(0 to 1 by .1) label=(h=1.5 'Depth') length=4in;
	goptions colors=(blue black red green gold cyan) i=join;

	data _null_;
		num = symget('model_num');
		do i=1 to num;
			put 'symbol' i ' i=join v=none;';
		end;
	run;

	proc gplot data = ds.total_confusion_matrix;
		plot lift*depth=model
		/ vaxis=axis1 haxis=axis2;
		title1 c=darkblue h=1.5 f=swissb "Lift Chart";
	run; quit;

	proc print data=ds.total_confusion_matrix label;
		var lift depth model cutoff;
		label lift="Lift" depth="Depth";
	run;

	/* plot the roc */
	axis1 order=(0 to 1 by .2) label=(h=1.5 'Sensitivity') length=4in;
	axis2 order=(0 to 1 by .2) label=(h=1.5 '1-Specificity') length=4in;

	proc gplot data = ds.total_confusion_matrix;
		plot sensitivity*_specificity=model
		/ vaxis=axis1 haxis=axis2;
		title1 c=darkblue h=1.5 f=swissb "Roc Chart";
	run; quit;

	proc print data=ds.total_confusion_matrix label;
		var sensitivity _specificity model cutoff;
		label sensitivity="Sensitivity" _specificity="1-Specificity";
	run;

	/* plot the gain */
	axis1 order=(0 to 1 by .2) label=(h=1.5 'PV_Plus') length=4in;
	axis2 order=(0 to 1 by .2) label=(h=1.5 'Depth') length=4in;

	proc gplot data = ds.total_confusion_matrix;
		plot pv_plus*depth=model
		/ vaxis=axis1 haxis=axis2;
		title1 c=darkblue h=1.5 f=swissb "Gain Chart";
	run; quit;

	proc print data=ds.total_confusion_matrix label;
		var pv_plus depth model cutoff;
	run;
%mend plot;

%macro gc;
	/* garbage clean */
	proc sql;
		drop table ds.total_confusion_matrix;
		drop table ds.confusion_matrix;
		drop table ds.score_output_temp;
	quit;

	filename cm;
%mend gc;
