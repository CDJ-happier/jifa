<!--
    Copyright (c) 2023 Contributors to the Eclipse Foundation

    See the NOTICE file(s) distributed with this work for additional
    information regarding copyright ownership.

    This program and the accompanying materials are made available under the
    terms of the Eclipse Public License 2.0 which is available at
    http://www.eclipse.org/legal/epl-2.0

    SPDX-License-Identifier: EPL-2.0
 -->
<script setup lang="ts">
import { useAnalysisApiRequester } from '@/composables/analysis-api-requester';
import { t } from '@/i18n/i18n';
import { getIcon } from '@/components/heapdump/icon-helper';
import { prettySize } from '@/support/utils';
import { useSelectedObject } from '@/composables/heapdump/selected-object';

const { request } = useAnalysisApiRequester();
const { selectedObjectId } = useSelectedObject();

const records = ref();
const slices = ref();
const names = ref();
const loading = ref(true);
const noData = ref(false);

// Stacktrace dialog state
const stacktraceVisible = ref(false);
const stacktraceLoading = ref(false);
const stacktraceFrames = ref<any[]>([]);
const stacktraceTitle = ref('');

function onClick(id) {
  selectedObjectId.value = id;
}

interface Record {
  desc: any;
  paths?: any;
  threadObjectId?: number;
}

interface Report {
  useful: boolean;
  records?: Record[];
  slices?: any[];
}

// Replace mat://detail_result/Links%2F0|1 with clickable spans, keyed by record index.
// Links/0 = stacktrace, Links/1 = stacktrace with local variables (shown the same way here).
function processDesc(desc: string, recordIndex: number): string {
  return desc.replace(
    /href="mat:\/\/detail_result\/Links%2F(\d+)"/g,
    (_, linkIndex) =>
      `href="javascript:void(0)" data-leak-link="${recordIndex}:${linkIndex}" style="cursor:pointer"`
  );
}

function handleDescClick(event: MouseEvent, record: Record) {
  const target = event.target as HTMLElement;
  const link = target.closest('[data-leak-link]');
  if (!link) return;
  const [, ] = (link.getAttribute('data-leak-link') || '').split(':');
  const threadId = record.threadObjectId ?? -1;
  if (threadId < 0) return;
  showStacktrace(threadId, record);
}

async function showStacktrace(objectId: number, record: Record) {
  stacktraceVisible.value = true;
  stacktraceLoading.value = true;
  stacktraceTitle.value = record.name;
  stacktraceFrames.value = [];
  try {
    const frames = await request('stackTrace', { objectId });
    stacktraceFrames.value = frames || [];
  } catch {
    stacktraceFrames.value = [];
  } finally {
    stacktraceLoading.value = false;
  }
}

onMounted(() => {
  request('leak.report').then((resp: Report) => {
    if (resp.useful) {
      records.value = resp.records;
      slices.value = resp.slices;

      names.value = [];
      records.value.forEach((r) => {
        names.value.push(r.name);
      });
    } else {
      noData.value = true;
    }
    loading.value = false;
  }).catch(() => {
    loading.value = false;
    noData.value = true;
  });
});
</script>
<template>
  <el-scrollbar v-loading="loading" v-if="!noData">
    <el-collapse v-if="names" v-model="names" style="width: 100%">
      <el-collapse-item v-for="(record, idx) in records" :title="record.name" :name="record.name">
        <el-tabs tab-position="left">
          <el-tab-pane :label="t('common.description')">
            <div v-html="processDesc(record.desc, idx)" @click="handleDescClick($event, record)"></div>
          </el-tab-pane>
          <el-tab-pane :label="t('common.detail')" v-if="record.paths">
            <el-tree
              :data="record.paths"
              node-key="objectId"
              default-expand-all
              :expand-on-click-node="false"
            >
              <template #default="{ node, data }">
                <div class="ej-tree-node" @click="onClick(data.objectId)">
                  <div style="display: flex; align-items: center">
                    <img :src="getIcon(data.gCRoot, data.objectType)" style="margin-right: 5px" />
                    {{ data.label }}
                  </div>
                  <span>
                    {{ prettySize(data.shallowSize) }} / {{ prettySize(data.retainedSize) }}
                  </span>
                </div>
              </template>
            </el-tree>
          </el-tab-pane>
        </el-tabs>
      </el-collapse-item>
    </el-collapse>
  </el-scrollbar>
  <div
    style="height: 100%; display: flex; justify-content: center; align-items: center; width: 100%"
    v-else
  >
    <el-empty :image-size="200" :description="t('common.noData')" />
  </div>

  <!-- Stacktrace dialog -->
  <el-dialog v-model="stacktraceVisible" :title="stacktraceTitle + ' - Stack Trace'" width="70%" top="5vh">
    <div v-loading="stacktraceLoading" style="min-height: 100px;">
      <el-empty v-if="!stacktraceLoading && stacktraceFrames.length === 0" description="No stack trace available" :image-size="60" />
      <el-table v-else :data="stacktraceFrames" stripe size="small" style="width:100%">
        <el-table-column type="index" width="50" />
        <el-table-column prop="stack" label="Frame" show-overflow-tooltip />
        <el-table-column prop="maxLocalRetained" label="Max Local Retained" width="160" align="right">
          <template #default="{ row }">{{ row.maxLocalRetained > 0 ? prettySize(row.maxLocalRetained) : '' }}</template>
        </el-table-column>
      </el-table>
    </div>
  </el-dialog>
</template>
<style scoped>
.ej-tree-node {
  flex: 1;
  display: flex;
  font-size: 12px;
  padding-right: 8px;
  justify-content: space-between;
}
</style>
