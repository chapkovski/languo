from django.views.generic import DetailView, UpdateView, TemplateView
from django.template.loader import render_to_string
from .models import CQ, Constants
from django.http import JsonResponse
import logging
from django import forms
import json
from django.core.exceptions import ValidationError


class QForm(forms.ModelForm):
    answer = forms.IntegerField(widget=forms.RadioSelect(choices=((0, 0), (1, 1))))

    class Meta:
        model = CQ
        fields = ['answer']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices = [(i, j) for i, j in enumerate(json.loads(self.instance.choices))]
        self.fields['answer'].widget.choices = choices

    def clean_answer(self):
        data = self.cleaned_data['answer']
        if data != self.instance.correct:
            self.instance.counter+=1
            self.instance.save()
            raise ValidationError(self.instance.owner.session.config.get('err_msg', Constants.CQ_ERR_DEFAULT_MSG))
        return data


logger = logging.getLogger(__name__)


class NoMoreCqs(TemplateView):
    url_name = 'no_more_cqs'
    url_pattern = 'quiz/<participant_code>/no_more'
    template_name = 'main/includes/no_more.html'

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        context = self.get_context_data(**kwargs)
        html_form = render_to_string(self.template_name,
                                     context,
                                     request=request,
                                     )

        return JsonResponse(dict(form_data=html_form, no_more_cq=True))


class QuizQuestionView(UpdateView):
    """
    Single quiz question
    """
    url_pattern = 'quiz/<int:pk>'
    url_name = 'single_quiz_question'
    template_name = 'main/includes/single_cq.html'

    model = CQ
    form_class = QForm

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        context = self.get_context_data()
        html_form = render_to_string(self.template_name,
                                     context,
                                     request=self.request,
                                     )

        return JsonResponse(dict(form_data=html_form))

    def get_success_url(self):
        return self.get_object().owner.get_quiz_url()

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        return c

    def form_valid(self, form):
        form.save()
        available_q = self.get_object().owner.cqs.filter(answer__isnull=True).first()

        if not available_q:
            return JsonResponse(dict(form_is_valid=True, next_q=self.get_success_url(), no_more_cq=True))
        context = self.get_context_data()
        html_form = render_to_string(self.template_name,
                                     context,
                                     request=self.request,
                                     )
        return JsonResponse(dict(form_is_valid=True,
                                 next_q=self.get_success_url(),
                                 form_data=html_form),
                            )

    def form_invalid(self, form):
        context = self.get_context_data()
        html_form = render_to_string(self.template_name,
                                     context,
                                     request=self.request,
                                     )

        return JsonResponse(dict(form_is_valid=False,
                                 next_q=self.get_success_url(),
                                 form_data=html_form),
                            )
