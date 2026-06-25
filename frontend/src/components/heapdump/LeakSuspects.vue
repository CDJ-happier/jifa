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
import FrameIcon from '@/assets/heapdump/stack_frame.gif';
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
const stacktraceTitle = ref('');
const showLocals = ref(false);      // whether to eagerly show local variables
const stacktraceThreadObjectId = ref(-1);

interface StackNode {
  id: string;
  label: string;
  depth: number;       // 1-based frame index (0 = root placeholder)
  hasLocal: boolean;
  maxLocalsRetainedSize: number;
  firstNonNativeFrame: boolean;
  children?: any[];
  _loaded?: boolean;
}

const stacktraceData = ref<StackNode[]>([]);

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

// Replace mat://detail_result/Links%2F0|1 with clickable spans.
// Links/0 = stacktrace only, Links/1 = stacktrace with local variables.
function processDesc(desc: string, record: Record): string {
  if (!record.threadObjectId || record.threadObjectId < 0) {
    // Not a thread suspect — strip mat:// links entirely, leave link text
    return desc.replace(
      /<a\s+href="mat:\/\/[^"]*"[^>]*>(.*?)<\/a>/g,
      '<span style="color:#999;text-decoration:line-through">$1</span>'
    );
  }
  return desc.replace(
    /href="mat:\/\/detail_result\/Links%2F(\d+)"/g,
    (_, linkIndex) =>
      `href="javascript:void(0)" data-leak-link="${linkIndex}" style="cursor:pointer;color:#409EFF"`
  );
}

function handleDescClick(event: MouseEvent, record: Record) {
  const target = event.target as HTMLElement;
  const link = target.closest('[data-leak-link]');
  if (!link || !record.threadObjectId || record.threadObjectId < 0) return;
  const linkIndex = Number(link.getAttribute('data-leak-link'));
  showStacktraceDialog(record.threadObjectId, record, linkIndex === 1);
}

async function showStacktraceDialog(objectId: number, record: Record, withLocals: boolean) {
  stacktraceVisible.value = true;
  stacktraceLoading.value = true;
  stacktraceTitle.value = record.name;
  showLocals.value = withLocals;
  stacktraceThreadObjectId.value = objectId;
  stacktraceData.value = [];

  try {
    const frames: any[] = await request('stackTrace', { objectId }) || [];
    stacktraceData.value = frames.map((f, i) => ({
      id: `frame-${i}`,
      label: f.stack,
      depth: i + 1,
      hasLocal: f.hasLocal,
      maxLocalsRetainedSize: f.maxLocalsRetainedSize || 0,
      firstNonNativeFrame: f.firstNonNativeFrame,
      children: f.hasLocal ? [] : undefined,
      _loaded: false
    }));
  } catch {
    stacktraceData.value = [];
  } finally {
    stacktraceLoading.value = false;
  }
}

async function loadLocals(node: StackNode) {
  if (node._loaded || !node.hasLocal) return;
  node._loaded = true;
  try {
    const locals = await request('locals', {
      objectId: stacktraceThreadObjectId.value,
      depth: node.depth,
      firstNonNativeFrame: node.firstNonNativeFrame
    });
    node.children = (locals || []).map((v, i) => ({
      id: `${node.id}-local-${i}`,
      label: v.label || v.name || String(v.objectId),
      objectId: v.objectId,
      objectType: v.objectType,
      gCRoot: v.gCRoot,
      shallowSize: v.shallowSize,
      retainedSize: v.retainedSize,
      isLocal: true
    }));
  } catch {
    node.children = [];
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
      <el-collapse-item v-for="record in records" :title="record.name" :name="record.name">
        <el-tabs tab-position="left">
          <el-tab-pane :label="t('common.description')">
            <div v-html="processDesc(record.desc, record)" @click="handleDescClick($event, record)"></div>
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

  <!-- Stacktrace dialog with expandable local variables -->
  <el-dialog v-model="stacktraceVisible" :title="stacktraceTitle + ' — Stack Trace'" width="72%" top="4vh" destroy-on-close>
    <div v-loading="stacktraceLoading" style="min-height: 80px;">
      <el-empty v-if="!stacktraceLoading && stacktraceData.length === 0"
                description="No stack trace available" :image-size="60" />
      <el-tree
        v-else
        :data="stacktraceData"
        node-key="id"
        :default-expand-all="showLocals"
        :expand-on-click-node="false"
        lazy
        :load="(node, resolve) => { loadLocals(node.data); resolve(node.data.children || []); }"
        style="font-size: 13px;"
        @node-expand="(data) => loadLocals(data)"
      >
        <template #default="{ data }">
          <!-- Frame node -->
          <div v-if="!data.isLocal" class="st-frame">
            <img :src="FrameIcon" style="margin-right:6px;vertical-align:middle" />
            <span :style="data.firstNonNativeFrame ? 'font-weight:600' : ''">{{ data.label }}</span>
            <span v-if="data.maxLocalsRetainedSize > 0" class="st-size">
              {{ prettySize(data.maxLocalsRetainedSize) }}
            </span>
          </div>
          <!-- Local variable node -->
          <div v-else class="st-local" @click="onClick(data.objectId)">
            <img :src="getIcon(data.gCRoot, data.objectType)" style="margin-right:6px;vertical-align:middle" />
            <span>{{ data.label }}</span>
            <span v-if="data.shallowSize || data.retainedSize" class="st-size">
              {{ prettySize(data.shallowSize) }} / {{ prettySize(data.retainedSize) }}
            </span>
          </div>
        </template>
      </el-tree>
    </div>
    <template #footer>
      <span style="font-size:12px;color:#999;">
        Bold frame = first non-native frame.
        {{ showLocals ? 'Showing local variables per frame.' : 'Click a frame to expand local variables.' }}
      </span>
    </template>
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
.st-frame {
  display: flex;
  align-items: center;
  font-size: 13px;
  gap: 4px;
}
.st-local {
  display: flex;
  align-items: center;
  font-size: 12px;
  gap: 4px;
  cursor: pointer;
  color: #606266;
}
.st-size {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>
