<template lang="html">
  <div class="container biz-create-success">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="plugin-new-version-loading"
      class="app-container middle"
    >
      <div class="new-version">
        <paas-plugin-title />
        <div
          v-if="curVersion.current_release"
          class="summary-box status"
        >
          <div class="wrapper default-box">
            <div class="fl mr25">
              {{ $t('当前版本：') }} {{ curVersion.current_release.version || '--' }}
            </div>
            <div class="fl mr25">
              {{ $t('代码分支：') }} {{ curVersion.current_release.source_version_name || '--' }}
            </div>
            <div class="fl mr25">
              {{ $t('CommitID：') }} {{ curVersion.current_release.source_hash || '--' }}
            </div>
            <div class="fl">
              {{ $t('由') }} {{ curVersion.current_release.creator || '--' }} {{ $t(' 于 ') }} {{ curVersion.current_release.created }} {{ $t('发布') }}
            </div>
          </div>
        </div>

        <!-- 表单 -->
        <div class="form-box">
          <bk-form
            ref="versionForm"
            :label-width="120"
            :model="curVersion"
            :rules="rules"
          >
            <bk-form-item
              :label="$t('代码仓库')"
              class="code-warehouse"
            >
              <bk-input
                v-model="curVersion.repository"
                :placeholder="$t('仓库地址')"
                readonly
              />
              <div class="icon-wrapper">
                <a
                  :href="curVersion.repository"
                  target="_blank"
                  style="color: #979BA5;"
                ><i class="paasng-icon paasng-jump-link icon-cls-link mr5" /></a>
                <i
                  v-copy="curVersion.repository"
                  class="paasng-icon paasng-general-copy icon-cls-copy"
                />
              </div>
            </bk-form-item>
            <bk-form-item
              :label="$t('代码分支')"
              :required="true"
              :property="'source_versions'"
            >
              <bk-select
                v-model="curVersion.source_versions"
                :disabled="false"
                ext-cls="select-custom"
                searchable
              >
                <bk-option
                  v-for="option in sourceVersions"
                  :id="option.name"
                  :key="option.name"
                  :name="option.name"
                />
              </bk-select>
              <div class="ribbon">
                <div
                  v-if="curVersion.current_release"
                  class="mr10"
                  @click="handleShowCommits"
                >
                  <i class="paasng-icon paasng-diff-line" />
                  <span>{{ $t('代码差异') }}</span>
                </div>
              </div>
            </bk-form-item>
            <bk-form-item
              v-if="curVersion.version_no === 'automatic'"
              :label="$t('版本类型')"
              :required="true"
              :property="'version'"
              :error-display-type="'normal'"
            >
              <bk-radio-group
                v-model="curVersion.version"
                @change="changeVersionType"
              >
                <bk-radio
                  v-bk-tooltips.top="$t('非兼容式升级时使用')"
                  :value="curVersion.semver_choices.major"
                >
                  <span v-dashed="12">{{ $t('重大版本') }}</span>
                </bk-radio>
                <bk-radio
                  v-bk-tooltips.top="$t('兼容式功能更新时使用')"
                  :value="curVersion.semver_choices.minor"
                >
                  <span v-dashed="12">{{ $t('次版本') }}</span>
                </bk-radio>
                <bk-radio
                  v-bk-tooltips.top="$t('兼容式问题修正时使用')"
                  :value="curVersion.semver_choices.patch"
                >
                  <span v-dashed="12">{{ $t('修正版本') }}</span>
                </bk-radio>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              :label="$t('版本号')"
              :required="true"
              :property="'version'"
            >
              <bk-input
                v-model="curVersion.version"
                :placeholder="$t('版本号')"
                :disabled="curVersion.version_no !== 'self-fill'"
              />
            </bk-form-item>
            <bk-form-item
              :label="$t('版本日志')"
              :required="true"
              :property="'comment'"
            >
              <bk-input
                v-model="curVersion.comment"
                :rows="5"
                type="textarea"
              />
            </bk-form-item>
            <bk-form-item label="">
              <div
                v-bk-tooltips.top="{ content: $t('已有发布任务进行中'), disabled: !isPending }"
                style="display: inline-block;"
              >
                <bk-button
                  theme="primary"
                  :loading="isSubmitLoading"
                  :disabled="isPending ? true : false"
                  @click="submitVersionForm"
                >
                  {{ $t('提交并发布') }}
                </bk-button>
              </div>
            </bk-form-item>
          </bk-form>
        </div>
      </div>
    </paas-content-loader>

    <!-- 详情 -->
    <bk-sideslider
      :is-show.sync="versionDetail.isShow"
      :quick-close="true"
      :width="960"
    >
      <div slot="header">
        {{ $t('测试详情') }}
      </div>
      <div
        slot="content"
        class="p20"
      >
        <bk-table
          v-bkloading="{ isLoading: isLogLoading }"
          class="ps-version-list"
          :data="versionList"
          :outer-border="false"
          :size="'small'"
          :pagination="pagination"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column
            :label="$t('Commit ID')"
            prop="name"
            :show-overflow-tooltip="true"
            :render-header="$renderHeader"
          />
          <bk-table-column
            :label="$t('状态')"
            prop="environment_name"
          >
            <template slot-scope="props">
              <span v-if="props.row.environment_name === 'stag'"> {{ $t('已测试') }} </span>
              <span v-else> {{ $t('未测试') }} </span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('提交者')"
            prop="operator"
            :render-header="$renderHeader"
          />
          <bk-table-column
            :label="$t('提交时间')"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              <span v-bk-tooltips="row.message">{{ row.message || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('log')">
            <template slot-scope="{ row }">
              <span v-bk-tooltips="row.message">{{ row.message || '--' }}</span>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </bk-sideslider>

    <bk-dialog
      v-model="newVersionConfig.visible"
      theme="primary"
      :mask-close="false"
      :title="`${$t('确认新建版本')}：${curVersion.version}`"
      @confirm="handlerConfirm"
      @cancel="handlerCancel"
    >
      <template v-if="curVersionData.source_versions">
        <div class="version-tips-item">
          <span>{{ $t('代码分支：') }}{{ curVersionData.source_versions[0].name }}</span>
        </div>
        <div class="version-tips-item">
          <span>{{ $t('代码更新时间：') }}{{ formatTime(curVersionData.source_versions[0].last_update) }}</span>
        </div>
        <div class="version-tips-item">
          <span>Commit Message: {{ curVersionData.source_versions[0].message }}</span>
        </div>
      </template>
    </bk-dialog>
  </div>
</template>

<script>
    import pluginBaseMixin from '@/mixins/plugin-base-mixin';
    import paasPluginTitle from '@/components/pass-plugin-title';
    import { formatTime } from '@/common/tools';

    export default {
        components: {
            paasPluginTitle
        },
        mixins: [pluginBaseMixin],
        data () {
            return {
                isLoading: false,
                versionDetail: {
                    isShow: false
                },
                versionList: [],
                pagination: {
                    current: 1,
                    count: 0,
                    limit: 10
                },
                curVersion: {
                    // 仓库地址
                    repository: '',
                    // 代码分支
                    source_versions: '',
                    // 版本类型
                    semver_choices: {},
                    // 版本号
                    version: '',
                    // 版本日志
                    comment: ''
                },
                sourceVersions: [],
                isLogLoading: false,
                isSubmitLoading: false,
                newVersionConfig: {
                    visible: false
                },
                curVersionData: {},
                formatTime: formatTime,
                rules: {
                    source_versions: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ],
                    version: [
                        {
                            required: true,
                            message: this.$t('请选择版本类型'),
                            trigger: 'blur'
                        }
                    ],
                    comment: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ]
                }
            };
        },
        computed: {
            isPending () {
                return this.$route.query.isPending;
            }
        },
        watch: {
            'curVersion.source_versions' (value) {
                if (this.curVersion.version_no === 'revision' || this.curVersion.version_no === 'commit-hash') {
                    const versionData = this.sourceVersions.filter(item => item.name === this.curVersion.source_versions);
                    if (this.curVersion.version_no === 'revision') {
                        this.curVersion.version = versionData[0].name;
                    } else {
                        this.curVersion.version = versionData[0].revision;
                    }
                }
            }
        },
        created () {
            this.init();
        },
        methods: {
            init () {
                this.getNewVersionFormat();
            },

            // 获取新建版本表单格式
            async getNewVersionFormat () {
                this.isLoading = true;
                const data = {
                    pdId: this.pdId,
                    pluginId: this.pluginId
                };
                try {
                    const res = await this.$store.dispatch('plugin/getNewVersionFormat', data);
                    this.curVersionData = res;
                    this.curVersion.doc = res.doc;
                    this.curVersion.current_release = res.current_release;
                    // 代码仓库
                    this.curVersion.repository = res.source_versions[0].url;
                    this.sourceVersions = res.source_versions;
                    // version_no 版本号生成规则, 自动生成(automatic),与代码版本一致(revision),与提交哈希一致(commit-hash),用户自助填写(self-fill)
                    this.curVersion.semver_choices = res.semver_choices;
                    this.curVersion.source_versions = res.source_versions[0].name;
                    if (res.version_no === 'revision') {
                        // 与代码版本一致(revision)
                        this.curVersion.version = res.source_versions[0].name;
                    } else if (res.version_no === 'commit-hash') {
                        // 提交哈希一致(commit-hash)
                        this.curVersion.version = res.source_versions[0].revision;
                    } else if (res.version_no === 'automatic') {
                        // 自动生成(automatic), 版本类型用户自行选择
                        this.curVersion.version = '';
                    } else if (res.version_no === 'self-fill') {
                        // 用户自助填写(self-fill)
                        this.curVersion.version = '';
                    }
                    this.curVersion.version_no = res.version_no;
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },

            submitVersionForm () {
                this.$refs.versionForm.validate().then(validator => {
                    this.newVersionConfig.visible = true;
                    // this.createVersion();
                });
            },

            // 新建版本并发布
            async createVersion () {
                this.isSubmitLoading = true;
                // 当前选中分支的数据
                const versionData = this.sourceVersions.filter(item => item.name === this.curVersion.source_versions);

                const data = {
                    source_version_type: versionData[0].type,
                    source_version_name: versionData[0].name,
                    version: this.curVersion.version,
                    comment: this.curVersion.comment
                };

                // 仅 versionNo=automatic 需要传递
                if (this.curVersion.version_no === 'automatic') {
                    for (const key in this.curVersion.semver_choices) {
                        if (this.curVersion.semver_choices[key] === this.curVersion.version) {
                            data.semver_type = key;
                        }
                    }
                }

                const params = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    data
                };
                try {
                    const res = await this.$store.dispatch('plugin/createVersion', params);
                    this.$bkMessage({
                        theme: 'success',
                        message: this.$t('新建成功!')
                    });
                    // 跳转至发布详情
                    this.goRelease(res);
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    this.isSubmitLoading = false;
                }
            },

            goBack () {
                this.$router.push({
                    name: 'pluginVersionManager'
                });
            },

            goRelease (data) {
                this.$router.push({
                    name: 'pluginVersionRelease',
                    query: {
                        release_id: data.id
                    }
                });
            },

            async handleShowCommits () {
                if (!this.curVersion.source_versions) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('请选择代码分支')
                    });
                    return false;
                }

                const fromRevision = this.curVersion.current_release.source_hash;
                const curCodeItem = this.sourceVersions.filter(item => item.name === this.curVersion.source_versions);
                const toRevision = `${curCodeItem[0].type}:${curCodeItem[0].name}`;
                const win = window.open();
                const res = await this.$store.dispatch('plugin/getGitCompareUrl', {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    fromRevision,
                    toRevision
                });
                win.location.href = res.result;
            },

            handlerConfirm () {
                this.createVersion();
            },

            handlerCancel () {
                this.isSubmitLoading = false;
            },

            changeVersionType () {
                this.$refs.versionForm.validate();
            }
        }
    };
</script>

<style lang="scss" scoped>
    .app-container {
      padding: 0;
      margin-top: 8px;
    }
    .header-title {
        display: flex;
        align-items: center;
        .app-code {
            color: #979BA5;
        }
        .arrows {
            margin: 0 9px;
            transform: rotate(-90deg);
            font-size: 12px;
            font-weight: 600;
            color: #979ba5;
        }
    }

    .detail-wrapper {
        .item-info {
            display: flex;
            height: 40px;
            line-height: 40px;
            border-top: 1px solid #dfe0e5;

            &:last-child {
                border-bottom: 1px solid #dfe0e5;
            }

            .describe,
            .content {
                display: flex;
                align-items: center;
            }

            .describe {
                flex-direction: row-reverse;
                width: 100px;
                text-align: right;
                padding-right: 16px;
                font-size: 12px;
                color: #979BA5;
                background: #FAFBFD;
            }
            .content {
                flex: 1;
                font-size: 12px;
                color: #63656E;
                padding: 10px 0 10px 16px;
                border-left: 1px solid #F0F1F5;
            }
        }

        .h-auto {
            height: auto;
            line-height: 22px;
        }
    }

    .detail-doc {
        color: #3A84FF;
        cursor: pointer;
    }

    .form-box {
        width: 650px;

        & /deep/ .bk-form-control .group-box {
            border-left: none;
            border-color: #3A84FF !important;
        }

        .icon-wrapper {
            display: flex;
            align-items: center;
            position: absolute;
            right: 0px;
            top: 0px;
            height: 100%;
            font-size: 16px;
            padding-right: 6px;
            color: #979BA5;

            .icon-cls-link:hover,
            .icon-cls-copy:hover {
                cursor: pointer;
                color: #3A84FF;
            }
        }

        .ribbon {
            display: flex;
            position: absolute;
            right: -98px;
            top: 0px;
            color: #3A84FF;

            div {
                cursor: pointer;
            }
        }

        .environment-wrapper {
            margin-top: 5px;
            padding: 5px 0;
            background: #F5F7FA;
            border-radius: 2px;
            padding-left: 28px;
        }
    }

    .icon-cls-return {
        font-weight: 700;
        font-size: 16px;
        cursor: pointer;
        color: #3A84FF;
    }

    .summary-box {
        padding: 10px 0 20px;
        background: #FFF;
        font-size: 12px;

        // & + .summary-box {
        //     padding-top: 0;
        // }

        .wrapper {
            // padding: 20px;
            // background: #F5F6FA;
            // border-radius: 2px;
            // padding: 11px 12px 11px 20px;
            // line-height: 16px;
            height: 64px;
            background: #F5F6FA;
            border-radius: 2px;
            line-height: 64px;
            padding: 0 20px;

            &::after {
                display: block;
                clear: both;
                content: "";
                font-size: 0;
                height: 0;
                visibility: hidden;
            }

            &.default-box {
                padding: 11px 12px 11px 20px;
                height: auto;
                line-height: 16px;
                color: #979BA5;
                .span {
                    height: 16px;
                }
            }

            &.not-deploy {
                height: 42px;
                line-height: 42px;
            }

            &.primary {
                background: #E1ECFF;
                color: #979BA5;
            }

            &.warning {
                background: #FFF4E2;
                border-color: #FFDFAC;

                .paasng-icon {
                    color: #fe9f07;
                }
            }

            &.danger {
                background: #FFECEC;
                color: #979BA5;

                .paasng-icon {
                    color: #eb3635;
                    position: relative;
                    top: 4px;
                    font-size: 32px;
                }
            }

            &.success {
                background: #E7FCFA;
                color: #979BA5;

                .paasng-icon {
                    position: relative;
                    top: 4px;
                    color: #3fc06d;
                    font-size: 32px;
                }
            }
        }
    }

    .line {
        position: relative;
        margin: 26px 0;
        max-width: 1080px;
        min-width: 1080px;
        border-top: 1px solid #F0F1F5;
    }

    .plugin-top-title {
        margin: 16px 0;
    }

    .version-tips-item {
        color: #63656e;
        font-size: 12px;
        line-height: 20px;
        padding: 3px 0;
    }

</style>

<style lang="css">
    .form-box .code-warehouse .bk-form-input {
        padding-right: 50px !important;
    }
    .form-box .cls-test-env .bk-form-content .bk-form-control>.bk-form-radio:first-child {
        width: 82px;
    }
</style>
