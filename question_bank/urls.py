from django.urls import path
from .views import (
    SearchQuestionBankView, QuestionBankUpdateDeleteView,
    SecurityQuestionListView, SingleQuestionBankView, GenerateObservationQuestionBankView
)

urlpatterns = [
    # 搜索题库
    path('<int:project_id>/search/', SearchQuestionBankView.as_view(), name='search_question_bank'),

    # 修改、删除题库
    path('<int:question_bank_id>/', QuestionBankUpdateDeleteView.as_view(), name='update_delete_question_bank'),

    # 获取所有安全题库的内容
    path('security/', SecurityQuestionListView.as_view(), name='security_question_bank'),

    # 获取单个观测题库的具体内容
    path('<int:question_bank_id>/detail/', SingleQuestionBankView.as_view(), name='single_question_bank'),

    # 预留：生成观测题库
    path('<int:project_id>/generate/', GenerateObservationQuestionBankView.as_view(), name='generate_observation_bank'),
]
