<template lang="html">
  <div class="right-main">
    <app-top-bar
      :title="$t(title)"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />

    <paas-content-loader
      :is-loading="loading"
      placeholder="data-store-loading"
      :offset-top="30"
      class="app-container middle"
    >
      <div class="app-container fadeIn">
        <section v-show="!loading">
          <div class="middle bnone">
            <h4> {{ $t('已启用的服务') }} </h4>
            <div v-if="!loading">
              <ul
                v-if="serviceListBound.length !== 0"
                class="service-list"
              >
                <li
                  v-for="(item, index) in serviceListBound"
                  :key="index"
                >
                  <div class="service-item">
                    <router-link
                      v-if="!item.isShare"
                      :to="{ name: 'appServiceInner', params: { id: appCode, service: item.uuid, category_id: item.category.id } }"
                    >
                      <div class="badge">
                        <div class="logo">
                          <img
                            :src="item.logo"
                            alt=""
                          >
                        </div>
                        <span class="title">{{ item.display_name }}</span>
                      </div>
                      <div class="description">
                        {{ item.description }}
                      </div>
                    </router-link>
                    <router-link
                      v-else
                      :to="{ name: 'appServiceInnerShared', params: { id: appCode, service: item.service.uuid, category_id: item.service.category.id } }"
                    >
                      <div class="badge">
                        <i
                          v-bk-tooltips=" `${$t('共享自')} ${item.ref_module ? item.ref_module.name : ''}${$t('模块')}`"
                          class="paasng-icon paasng-info-circle ref-module-icon"
                        />
                        <div class="logo">
                          <img
                            :src="item.service.logo"
                            alt=""
                          >
                        </div>
                        <span class="title">{{ item.service.display_name }}</span>
                      </div>
                      <div class="description">
                        {{ item.service.description }}
                      </div>
                    </router-link>
                  </div>
                </li>
              </ul>
              <div v-if="serviceListBound.length === 0">
                <div class="ps-no-result multiNotes">
                  <table-empty
                    :empty-title="$t('暂未启用任何服务，请从下方选择开启。')"
                    empty
                  />
                </div>
              </div>
            </div>
          </div>
          <div class="middle bnone service">
            <h4> {{ $t('未启用的服务') }} </h4>
            <div v-if="!loading">
              <ul
                v-if="serviceListUnbound.length !== 0"
                class="service-list"
              >
                <li
                  v-for="(item, index) in serviceListUnbound"
                  :key="index"
                >
                  <div class="service-item service-item-with-console">
                    <router-link
                      target="_blank"
                      :to="{ name: 'serviceInnerPage', params: { category_id: item.category.id, name: item.name }, query: { name: item.display_name } }"
                    >
                      <div class="badge">
                        <div class="logo">
                          <img
                            :src="item.logo"
                            alt=""
                          >
                        </div>
                        <div class="title">
                          {{ item.display_name }}
                        </div>
                      </div>
                      <div class="dyna-info">
                        <i class="paasng-icon paasng-clipboard" /> {{ $t('简介') }}
                      </div>
                    </router-link>
                  </div>

                  <div class="service-console">
                    <a
                      v-if="isSmartApp"
                      v-bk-tooltips="$t('S-mart应用请在配置文件中设置并开启增强服务')"
                      class="ps-btn ps-btn-default ps-btn-disabled"
                    >
                      <template v-if="item.specifications.length">
                        <span v-dashed> {{ $t('配置并启用服务') }} </span>
                      </template>
                      <template v-else>
                        <section>
                          <span v-dashed> {{ $t('启用服务') }} </span>
                        </section>
                      </template>
                    </a>
                    <a
                      v-else
                      class="ps-btn ps-btn-default"
                      @click="enableService(item)"
                    >
                      <template v-if="item.specifications.length">
                        <span> {{ $t('配置并启用服务') }} </span>
                      </template>
                      <template v-else-if="serviceStates[item.uuid] === 'applying'">
                        <span> {{ $t('启用中...') }} </span>
                      </template>
                      <template v-else>
                        <span> {{ $t('启用服务') }} </span>
                      </template>
                    </a>
                    <bk-popconfirm
                      :ref="`${index}_popconfirmRef`"
                      trigger="click"
                      placement="bottom-end"
                      :confirm-button-is-text="false"
                      confirm-text=""
                      cancel-text=""
                    >
                      <div slot="content">
                        <bk-button
                          text
                          theme="primary"
                          @click="handleOpenExportDialog(item, index)"
                        >
                          {{ $t('从其它模块共享服务') }}
                        </bk-button>
                      </div>
                      <div class="export-wrapper">
                        <span class="paasng-icon paasng-down-shape" />
                      </div>
                    </bk-popconfirm>
                  </div>
                </li>
              </ul>

              <div v-if="serviceListUnbound.length === 0">
                <div class="ps-no-result">
                  <table-empty
                    :empty-title="$t('暂无未启用服务')"
                    empty
                  />
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </paas-content-loader>

    <shared-dialog
      :data="curData"
      :show.sync="isShowDialog"
      @on-success="handleExportSuccess"
    />
  </div>
</template>

<script>
    import _ from 'lodash';
    import appBaseMixin from '@/mixins/app-base-mixin';
    import appTopBar from '@/components/paas-app-bar';
    import SharedDialog from './comps/shared-dialog';

    export default {
        components: {
            appTopBar,
            SharedDialog
        },
        mixins: [appBaseMixin],
        data () {
            return {
                title: '',
                serviceListBound: [],
                serviceListUnbound: [],
                appid: '',
                loading: true,
                serviceStates: {},
                isShowDialog: false,
                curData: {}
            };
        },
        watch: {
            '$route' () {
                this.init();
            }
        },
        created () {
            this.init();
        },
        methods: {
            init () {
                this.loading = true;
                this.service_category_id = this.$route.params.category_id;

                const categoryUrl = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/services/categories/${this.service_category_id}/`;

                this.$http.get(categoryUrl).then((response) => {
                    const body = response.results;
                    const sharedData = JSON.parse(JSON.stringify(body.shared));
                    sharedData.forEach(item => {
                        item.isShare = true;
                    });
                    this.serviceListBound = body.bound.concat(sharedData);
                    this.serviceListUnbound = body.unbound;

                    const category = response.category;
                    this.title = category.name_zh_cn;

                    this.loading = false;
                });
            },

            handleExportSuccess () {
                this.init();
            },

            handleOpenExportDialog (payload, index) {
                this.curData = payload;
                this.isShowDialog = true;
                setTimeout(() => {
                    const $ref = this.$refs[`${index}_popconfirmRef`][0].$refs.popover;
                    $ref.instance.hide();
                });
            },

            enableService (service) {
                if (service.specifications.length) {
                    this.$router.push({
                        name: 'appServiceConfig',
                        params: {
                            id: this.appCode,
                            service: service.uuid,
                            category_id: service.category.id,
                            moduleId: this.curModuleId
                        }
                    });
                    return;
                }

                if (this.serviceStates[service.uuid] === 'applying') {
                    return;
                }

                this.$set(this.serviceStates, service.uuid, 'applying');
                const formData = {
                    service_id: service.uuid,
                    code: this.appCode,
                    module_name: this.curModuleId
                };
                const url = `${BACKEND_URL}/api/services/service-attachments/`;
                this.$http.post(url, formData).then((response) => {
                    this.serviceListBound.push(service);
                    _.remove(this.serviceListUnbound, service);
                    this.serviceStates[service.uuid] = 'applied';
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('服务启用成功')
                    });
                }, (resp) => {
                    this.serviceStates[service.uuid] = 'default';
                    this.$paasMessage({
                        theme: 'error',
                        message: resp.detail || this.$t('接口异常')
                    });
                });
            }
        }
    };
</script>

<style lang="scss" scoped>
    .multiNotes {
        p {
            line-height: 42px;
        }
    }

    .service-list {
        overflow: hidden;
        margin: 0 -6px 0 -6px;
    }

    .service-list li {
        padding: 0 6px 12px 6px;
        width: 25%;
        float: left;
    }

    .service-item {
        position: relative;
        border: solid 1px #e6e9ea;
        border-radius: 2px;
        transition: all .5s;
        cursor: pointer;
        a {
            display: block;
        }

        .dyna-info {
            font-size: 12px;
            position: absolute;
            display: none;
            top: 0;
            right: 0;
            margin: 4px 6px 0 0;
            color: #999;
        }

        .description {
            color: #999;
            font-size: 12px;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            padding: 8px 15px 16px 15px;
            text-align: center;
        }

        .badge {
            position: relative;
            text-align: center;
            .ref-module-icon {
                position: absolute;
                top: 10px;
                right: 10px;
                color: #63656e;
                cursor: default;
            }
            .logo {
                padding: 24px 0 0 0;

                img {
                    height: 48px;
                }
            }

            .title {
                font-weight: bold;
                color: #5d6075;
                line-height: 34px;
                overflow: hidden;
                padding: 10px 0;
                white-space: nowrap;
                text-overflow: ellipsis;
                max-width: 190px;
                display: inline-block;
            }
        }
    }

    .service-item:hover {
        border: solid 1px #3A84FF;
        box-shadow: 0 0 1px #5cadff;

        .dyna-info {
            display: block;
        }
    }

    .service-item-with-console {
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
    }

    .service-console {
        position: relative;
        display: flex;
        justify-content: space-between;
        color: #c4c4c4;

        a {
            width: calc(100% - 39px);
            border-top-width: 0;
            border-radius: 2px;
            border-top-left-radius: 0;
            border-top-right-radius: 0;
            display: block;
            line-height: 22px;
            font-size: 14px;

            &:not(.ps-btn-disabled) {
                &:hover {
                    color: white;
                    background: #3A84FF;
                }
            }
        }

        .export-wrapper {
            width: 39px;
            line-height: 39px;
            text-align: center;
            border-right: 1px solid #e5e5e5;
            border-bottom: 1px solid #e5e5e5;
            cursor: pointer;
        }
    }
</style>
