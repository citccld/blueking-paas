# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.cluster.shim import EnvClusterService, RegionClusterService
from paasng.accessories.iam.exceptions import BKIAMGatewayServiceError
from paasng.accessories.iam.helpers import (
    add_role_members,
    fetch_application_members,
    fetch_role_members,
    remove_user_all_roles,
)
from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_class
from paasng.engine.constants import ClusterType
from paasng.plat_admin.admin42.serializers.application import ApplicationDetailSLZ, ApplicationSLZ, BindEnvClusterSLZ
from paasng.plat_admin.admin42.utils.filters import ApplicationFilterBackend
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.applications.constants import AppFeatureFlag, ApplicationRole
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application, ApplicationFeatureFlag
from paasng.platform.applications.serializers import ApplicationFeatureFlagSLZ, ApplicationMemberSLZ
from paasng.platform.applications.signals import application_member_updated
from paasng.platform.applications.tasks import cal_app_resource_quotas, sync_developers_to_sentry
from paasng.platform.core.storages.redisdb import DefaultRediStore
from paasng.utils.error_codes import error_codes


class ApplicationListView(GenericTemplateView):
    """Application列表 的模板视图"""

    name = "应用列表"
    queryset = Application.objects.all()
    serializer_class = ApplicationSLZ
    template_name = "admin42/applications/list_applications.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    filter_backends = [ApplicationFilterBackend]

    def get_context_data(self, **kwargs):
        self.paginator.default_limit = 10
        if 'view' not in kwargs:
            kwargs['view'] = self

        # 获取所有应用的资源使用总量
        store = DefaultRediStore(rkey='quotas::app')
        app_resource_quotas = store.get()
        # 未获取到，则在在后台计算
        if not app_resource_quotas:
            cal_app_resource_quotas.delay()
        else:
            # 以获取到所有应用的资源使用量，则按资源使用率排序分页
            return self.get_app_resource_context_data(app_resource_quotas, **kwargs)

        data = self.list(self.request, *self.args, **self.kwargs)
        kwargs['application_list'] = data
        kwargs['pagination'] = self.get_pagination_context(self.request)
        return kwargs

    def get_app_resource_context_data(self, app_resource_quotas, **kwargs):
        # 手动按资源的使用量排序分页
        offset = self.paginator.get_offset(self.request)
        limit = self.paginator.get_limit(self.request)
        queryset = self.filter_queryset(self.get_queryset())

        if self.request.query_params.get('search_term'):
            # 有查询参数则不按资源用量排序
            page = queryset[offset : offset + limit]
        else:
            # 应用资源排序后的信息
            page_app_code_list = list(app_resource_quotas.keys())[offset : offset + limit]
            page = queryset.filter(code__in=page_app_code_list)

        data = self.get_serializer(page, many=True, context={"app_resource_quotas": app_resource_quotas}).data
        data = sorted(data, key=lambda item: item['resource_quotas']['memory'], reverse=True)
        kwargs['application_list'] = data

        # 没有调用默认的 paginate_queryset 方法，需要手动给 paginator 的参数赋值
        self.paginator.count = self.paginator.get_count(queryset)
        self.paginator.limit = limit
        self.paginator.offset = offset
        self.paginator.request = self.request
        kwargs['pagination'] = self.get_pagination_context(self.request)
        return kwargs

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ApplicationDetailBaseView(GenericTemplateView, ApplicationCodeInPathMixin):
    """Application详情概览页"""

    template_name = "admin42/applications/detail/base.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    # 描述当前高亮的导航栏
    name: str = ''

    def get_context_data(self, **kwargs):
        if 'view' not in kwargs:
            kwargs['view'] = self
        application = ApplicationDetailSLZ(self.get_application()).data
        kwargs['application'] = application
        kwargs['cluster_choices'] = [
            {'id': cluster.name, 'name': f"{cluster.name} -- {ClusterType.get_choice_label(cluster.type)}"}
            for cluster in RegionClusterService(application['region']).list_clusters()
        ]
        return kwargs

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ApplicationOverviewView(ApplicationDetailBaseView):
    """Application详情概览页"""

    queryset = Application.objects.all()
    serializer_class = ApplicationSLZ
    template_name = "admin42/applications/detail/overview.html"
    name = "概览"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs['USER_IS_ADMIN_IN_APP'] = self.request.user.username in fetch_role_members(
            self.get_application().code, ApplicationRole.ADMINISTRATOR
        )
        return kwargs


class AppEnvConfManageView(ApplicationCodeInPathMixin, viewsets.GenericViewSet):
    """应用部署环境配置管理"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def bind_cluster(self, request, code, module_name, environment):
        slz = BindEnvClusterSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        EnvClusterService(env=self.get_env_via_path()).bind_cluster(cluster_name=slz.validated_data["cluster_name"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationMembersManageView(ApplicationDetailBaseView):
    """Application 应用成员管理页"""

    template_name = "admin42/applications/detail/base_info/members.html"
    name = "成员管理"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs['ROLE_PERMISSION_SPEC'] = {
            ApplicationRole.ADMINISTRATOR.value: ['应用开发', '上线审核', '应用推广', '成员管理'],
            ApplicationRole.DEVELOPER.value: ['应用开发', '应用推广'],
            ApplicationRole.OPERATOR.value: ['上线审核', '应用推广'],
        }
        kwargs['PERMISSION_LIST'] = ['应用开发', '上线审核', '应用推广', '成员管理']
        kwargs['ROLE_CHOICES'] = {
            key: value
            for value, key in ApplicationRole.get_django_choices()
            if value in kwargs['ROLE_PERMISSION_SPEC'].keys()
        }

        return kwargs


class ApplicationMembersManageViewSet(ApplicationCodeInPathMixin, viewsets.GenericViewSet):
    """Application应用成员 CRUD 接口"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def list(self, request, *args, **kwargs):
        members = fetch_application_members(self.get_application().code)
        return Response(ApplicationMemberSLZ(members, many=True).data)

    def destroy(self, request, code):
        application = self.get_application()
        try:
            remove_user_all_roles(application.code, request.query_params["username"])
        except BKIAMGatewayServiceError as e:
            raise error_codes.DELETE_APP_MEMBERS_ERROR.f(e.message)

        self.sync_membership(application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, code):
        application = self.get_application()
        username, role = request.data['username'], request.data['role']

        try:
            remove_user_all_roles(application.code, username)
            add_role_members(application.code, ApplicationRole(role), username)
        except BKIAMGatewayServiceError as e:
            raise error_codes.UPDATE_APP_MEMBERS_ERROR.f(e.message)

        self.sync_membership(application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def sync_membership(self, application):
        sync_developers_to_sentry.delay(application.id)
        application_member_updated.send(sender=application, application=application)


class ApplicationFeatureFlagsView(ApplicationDetailBaseView):
    """Application应用特性管理页"""

    template_name = "admin42/applications/detail/base_info/app_feature_flags.html"
    name = "特性管理"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["APP_FEATUREFLAG_CHOICES"] = dict(AppFeatureFlag.get_django_choices())
        kwargs["feature_flag_list"] = ApplicationFeatureFlagSLZ(
            ApplicationFeatureFlag.objects.filter(application=self.get_application()), many=True
        ).data
        return kwargs


class ApplicationFeatureFlagsViewset(ApplicationCodeInPathMixin, viewsets.GenericViewSet):
    """Application应用特性 CRUD 接口"""

    serializer_class = ApplicationFeatureFlagSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def list(self, request, code):
        return Response(
            ApplicationFeatureFlagSLZ(
                ApplicationFeatureFlag.objects.filter(application=self.get_application()), many=True
            ).data
        )

    def update(self, request, code):
        application = self.get_application()
        application.feature_flag.set_feature(request.data["name"], request.data["effect"])
        return Response(status=status.HTTP_204_NO_CONTENT)
