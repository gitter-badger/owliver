from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from main import models
from main.models import Exam, Answer, ExamAnswerSheet, SectionAnswerSheet, McqAnswerToMcqOption
from custom_exceptions import CustomException, QuestionTypeNotImplemented
from scripts import add_anssheet, load_unicode

EAS = ExamAnswerSheet

import sys
import django
import os
from datetime import timedelta, datetime
from django.utils import timezone

def get_python_version():
	return ".".join([str(sys.version_info.major),str(sys.version_info.minor)])
def get_django_version():
	return django.get_version()[:4]

def about(request):
	context_dict = {}
	context_dict["python_version"] = get_python_version()
	context_dict["django_version"] = get_django_version()
	context_dict["contributors"] = ["Eklavya Sharma"]
	return render(request,"about.html",context_dict)

def index(request):
	return render(request,"index.html",{})

exam_not_started_str = "This exam has not begun"
exam_ended_str = "This exam has ended"

class InvalidUser(CustomException):
	exp_str = "This link does not belong to you"
	def __str__(self):
		return InvalidUser.exp_str
class InvalidFormData(CustomException):
	exp_str = "This form has invalid POST data. Either there is a bug in our code or some hacker is at work."
	def __str__(self):
		return InvalidFormData.exp_str

def base_response(request,body,title=None,h1=None):
	context_dict = {"base_body":body}
	if title:
		context_dict["base_title"] = title
	if h1:
		context_dict["base_h1"] = h1
	return render(request, "base.html", context_dict)

# Exam Lists =======================================================================================

def public_exam_list(request):
	context_dict = {"exam_list":Exam.objects.filter(owner__isnull=True)}
	context_dict["base_title"] = "Owliver - Public Exams"
	context_dict["base_h1"] = "Public Exams"
	return render(request,"exam_list.html",context_dict)

def user_exam_list(request,username):
	user = get_object_or_404(User,username=username)
	context_dict = {"exam_list":Exam.objects.filter(owner=user)}
	context_dict["base_title"] = "Owliver - {username}'s Exams".format(username=username)
	context_dict["base_h1"] = "Exams owned by "+username
	return render(request,"exam_list.html",context_dict)

@login_required
def eas_list(request):
	context_dict = {"eas_list":request.user.examanswersheet_set.all()}
	return render(request,"eas_list.html",context_dict)

def exam_cover(request,eid):
	exam = get_object_or_404(Exam,id=eid)
	context_dict = {"exam":exam}
	if exam.time_limit == timedelta(0):
		context_dict["infinite_time"] = True
	if request.user.is_authenticated():
		context_dict["can_attempt"] = exam.can_attempt(request.user)
	return render(request,"exam_cover.html",context_dict)

@login_required
def make_eas(request,eid):
	if request.method!="POST":
		raise Http404("This page is only accessible via POST")
	exam = get_object_or_404(Exam,id=eid)
	if exam.can_attempt(request.user):
		eas = add_anssheet.add_eas(exam,request.user)
		if "start" in request.POST:
			eas.set_timer()
		return HttpResponseRedirect(reverse("main:eas_list"))
	else:
		return base_response(request, "You do not have permission to attempt this exam.")

@login_required
def start_eas(request,eid):
	if request.method!="POST":
		raise Http404("This page is only accessible via POST")
	eas = get_object_or_404(ExamAnswerSheet,id=eid)
	if eas.user!=request.user:
		raise Http404(str(ParaayaAnswer()))
	if eas.get_timer_status() == EAS.TIMER_NOT_SET:
		eas.set_timer()
	return HttpResponseRedirect(reverse("main:eas_cover",args=(eas.id,)))

# Attempt ==========================================================================================

def exam_not_started(timer_status):
	return timer_status!=EAS.TIMER_IN_PROGRESS and timer_status!=EAS.TIMER_ENDED

def get_dict_with_eas_values(eas,current_user):
	if eas.user!=current_user:
		raise InvalidUser()
	context_dict = {"eas":eas}
	timer_status = eas.get_timer_status()
	context_dict["timer_status"] = timer_status
	context_dict["EAS"] = EAS
	if timer_status==EAS.TIMER_IN_PROGRESS:
		now = timezone.now()
		context_dict["elapsed_time"] = now - eas.start_time
		if eas.end_time!=None:
			context_dict["remaining_time"] = eas.end_time - now
	exam = eas.exam
	context_dict["exam"] = exam
	context_dict["can_view_solutions"] = (exam.can_view_solutions(current_user) and timer_status==EAS.TIMER_ENDED)
	return context_dict

@login_required
def eas_cover(request,eid):
	eid = int(eid)
	eas = get_object_or_404(ExamAnswerSheet, id=eid)
	try:
		context_dict = get_dict_with_eas_values(eas,request.user)
	except InvalidUser:
		return base_response(request, InvalidUser.exp_str)
	exam = context_dict["exam"]
	timer_status = context_dict["timer_status"]

	# Generate stats for result card
	sas_set = list(eas.sectionanswersheet_set.all())
	context_dict["sas_set"] = sas_set
	eas.corr=0; eas.wrong=0; eas.att=0; eas.na=0;
	eas.hints=0; eas.marks=0; eas.tot=0;
	hint_col = False
	for sas in sas_set:
		if sas.section.allowed_attempts==0 and timer_status!=EAS.TIMER_ENDED:
			sas.att, sas.na, sas.hints = sas.attempt_freq()
			sas.corr = ""; sas.wrong = ""; sas.marks = "";
		else:
			sas.corr, sas.wrong, sas.na, sas.hints, sas.marks = sas.result_freq()
			sas.att = sas.corr + sas.wrong
		if sas.section.hint_deduction>0:
			hint_col = True
		sas.tot = sas.na + sas.att
		attrs = ("corr","wrong","marks")
		for attr in attrs:
			if getattr(eas,attr)!="" and getattr(sas,attr)!="":
				setattr(eas,attr,getattr(eas,attr)+getattr(sas,attr))
			else:
				setattr(eas,attr,"")
		attrs = ("att","na","hints","tot")
		for attr in attrs:
			setattr(eas,attr,getattr(eas,attr)+getattr(sas,attr))
		context_dict["hint_col"] = hint_col
	return render(request,"eas_cover.html",context_dict)

def fill_dict_with_sas_values(context_dict,sas):
	context_dict["sas"] = sas
	context_dict["section"] = sas.section
	eas = sas.exam_answer_sheet

	qset = eas.sectionanswersheet_set.filter(id__lt=sas.id)
	# qset means queryset
	sasno = qset.count()+1
	context_dict["sasno"] = sasno
	# Check next and prev questions in same section
	if sasno>1:
		prevsid = qset.last().id
		context_dict["prevsecname"] = SectionAnswerSheet.objects.get(id=prevsid).section.name
	else:
		prevsid = None
	qset = eas.sectionanswersheet_set.filter(id__gt=sas.id)
	if qset.exists():
		nextsid = qset.first().id
		context_dict["nextsecname"] = SectionAnswerSheet.objects.get(id=nextsid).section.name
	else:
		nextsid = None

	context_dict["prevsid"] = prevsid
	context_dict["nextsid"] = nextsid

@login_required
def sas_cover(request,sid):
	sid = int(sid)
	sas = get_object_or_404(SectionAnswerSheet, id=sid)

	eas = sas.exam_answer_sheet
	try:
		context_dict = get_dict_with_eas_values(eas,request.user)
	except InvalidUser:
		return base_response(request, InvalidUser.exp_str)
	if exam_not_started(context_dict["timer_status"]):
		return base_response(request, exam_not_started_str)

	sas.corr, sas.wrong, sas.na, sas.hints, sas.marks = sas.result_freq()
	fill_dict_with_sas_values(context_dict, sas)
	context_dict["unicode_dict"] = load_unicode.unicode_dict
	return render(request,"sas_cover.html",context_dict)

def fill_dict_with_answer_values(context_dict,answer,verbose=False):
	context_dict["answer"] = answer
	sas = answer.section_answer_sheet
	section = sas.section
	special_question = answer.get_typed_question()
	special_answer = answer.get_special_answer()
	question = special_question.question

	if verbose:
		result = special_answer.result()
		if result==True:
			context_dict["result_str"] = "Correct"
			context_dict["marks"] = section.correct_marks
		elif result==False:
			context_dict["result_str"] = "Wrong"
			context_dict["marks"] = section.wrong_marks
		else:
			context_dict["result_str"] = "Not attempted"
			context_dict["marks"] = section.na_marks
		if answer.viewed_hint:
			context_dict["marks"]-= section.hint_deduction

	qset = sas.answer_set.filter(id__lt=answer.id)
	# qset means queryset, qno means question number
	qno = qset.count()+1
	context_dict["qno"] = qno
	# Check next and prev questions in same section
	if qno>1:
		prevaid = qset.last().id
	else:
		prevaid = None
	qset = sas.answer_set.filter(id__gt=answer.id)
	if qset.exists():
		nextaid = qset.first().id
	else:
		nextaid = None

#	# Check next and previous questions in different sections if not found in same section
#	if prevaid==None and prevsid!=None:
#		prevaid = SectionAnswerSheet.objects.get(id=prevsid).answer_set.last().id
#	if nextaid==None and nextsid!=None:
#		nextaid = SectionAnswerSheet.objects.get(id=nextsid).answer_set.first().id

	context_dict["prevaid"] = prevaid
	context_dict["nextaid"] = nextaid
	context_dict["qtype"] = special_question.get_qtype()
	context_dict["question"] = question
	context_dict["special_question"] = special_question
	context_dict["answer"] = answer
	context_dict["special_answer"] = special_answer

@login_required
def attempt_question(request,aid):
	aid = int(aid)
	answer = get_object_or_404(Answer, id=aid)
	sas = answer.section_answer_sheet
	eas = sas.exam_answer_sheet
	try:
		context_dict = get_dict_with_eas_values(eas,request.user)
	except InvalidUser:
		return base_response(request, InvalidUser.exp_str)
	timer_status = context_dict["timer_status"]
	if exam_not_started(timer_status):
		return base_response(exam_not_started_str)
	fill_dict_with_sas_values(context_dict,sas)
	fill_dict_with_answer_values(context_dict,answer,verbose=True)
	if timer_status==EAS.TIMER_IN_PROGRESS:
		folder="attempt"
	else:
		folder="review"

	qtype = context_dict["qtype"]
	special_answer = context_dict["special_answer"]
	special_question = context_dict["special_question"]
	if qtype=="text":
		if special_question.ignore_case:
			context_dict["case_sens"] = "No"
		else:
			context_dict["case_sens"] = "Yes"
	elif qtype=="mcq":
		option_list = list(special_question.mcqoption_set.all())
		chosen_options = set(special_answer.chosen_options.all())
		for option in option_list:
			option.is_chosen = (option in chosen_options)
		context_dict["option_list"] = option_list
	else:
		raise QuestionTypeNotImplemented(qtype)
	context_dict["unicode_dict"] = load_unicode.unicode_dict
	return render(request, os.path.join(folder,context_dict["qtype"]+"_question.html"), context_dict)

@login_required
def submit(request,aid):
	if request.method!="POST":
		raise Http404("This page is only accessible via POST")

	aid = int(aid)
	answer = get_object_or_404(Answer, id=aid)
	sas = answer.section_answer_sheet
	eas = sas.exam_answer_sheet
	try:
		context_dict = get_dict_with_eas_values(eas,request.user)
	except InvalidUser:
		return base_response(request, InvalidUser.exp_str)
	timer_status = context_dict["timer_status"]
	if timer_status==EAS.TIMER_ENDED:
		return base_response(request, exam_ended_str)
	elif timer_status!=EAS.TIMER_IN_PROGRESS:
		return base_response(request, exam_not_started_str)

	fill_dict_with_answer_values(context_dict,answer)

	# save response to database
	qtype = context_dict["qtype"]
	special_answer = context_dict["special_answer"]
	if qtype=="text":
		if "response" not in request.POST:
			raise InvalidFormData()
		special_answer.response=request.POST["response"]
	elif qtype=="mcq":
		special_answer.chosen_options.clear()
		chosen_option_ids = request.POST.getlist("response")
		for option_id in chosen_option_ids:
			link = McqAnswerToMcqOption(mcq_answer=special_answer,mcq_option_id=option_id)
			link.save()
	else:
		raise QuestionTypeNotImplemented(qtype)
	special_answer.save()

	# redirect
	if "submit" in request.POST:
		nextaid = aid
	elif "submit_and_next" in request.POST:
		nextaid = context_dict["nextaid"]
	else:
		raise InvalidFormData()
	if not nextaid:
		fill_dict_with_sas_values(context_dict,sas)
		nextsid = context_dict["nextsid"]
		if not nextsid:
			nextaid = aid
		else:
			return HttpResponseRedirect(reverse("main:sas_cover",args=(nextsid,)))
	return HttpResponseRedirect(reverse("main:attempt_question",args=(nextaid,)))

@login_required
def submit_eas(request,eid):
	if request.method!="POST":
		raise Http404("This page is only accessible via POST")
	eas = get_object_or_404(ExamAnswerSheet,id=eid)
	if eas.user!=request.user:
		raise Http404(InvalidUser.exp_str)
	timer_status = eas.get_timer_status()
	if timer_status == EAS.TIMER_IN_PROGRESS:
		eas.end_time = timezone.now()
		eas.save()
	elif timer_status == EAS.TIMER_NOT_STARTED:
		eas.end_time = eas.start_time
		eas.save()
	return HttpResponseRedirect(reverse("main:eas_cover",args=(eas.id,)))
