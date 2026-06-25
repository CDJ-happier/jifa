/********************************************************************************
 * Copyright (c) 2020, 2021 Contributors to the Eclipse Foundation
 *
 * See the NOTICE file(s) distributed with this work for additional
 * information regarding copyright ownership.
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0
 *
 * SPDX-License-Identifier: EPL-2.0
 ********************************************************************************/
package org.eclipse.jifa.hda.impl;

import org.eclipse.jifa.common.util.Validate;
import org.eclipse.mat.SnapshotException;
import org.eclipse.mat.query.IContextObject;
import org.eclipse.mat.query.IResultTree;
import org.eclipse.mat.snapshot.ISnapshot;
import org.eclipse.mat.snapshot.model.GCRootInfo;
import org.eclipse.mat.snapshot.model.IObject;
import org.eclipse.mat.snapshot.model.NamedReference;
import org.eclipse.mat.snapshot.query.IHeapObjectArgument;
import org.eclipse.mat.util.IProgressListener;
import org.eclipse.mat.util.VoidProgressListener;

import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import static org.eclipse.jifa.common.Constant.EMPTY_STRING;

public class Helper {
    public static final int ILLEGAL_OBJECT_ID = -1;

    public static IProgressListener VOID_LISTENER = new VoidProgressListener();

    public static int fetchObjectId(IContextObject context) {
        return context == null ? ILLEGAL_OBJECT_ID : context.getObjectId();
    }

    public static String suffix(ISnapshot snapshot, int objectId) throws SnapshotException {
        GCRootInfo[] gc = snapshot.getGCRootInfo(objectId);
        return gc != null ? GCRootInfo.getTypeSetAsString(gc) : EMPTY_STRING;
    }

    public static String suffix(GCRootInfo[] gcRootInfo) {
        return gcRootInfo != null ? GCRootInfo.getTypeSetAsString(gcRootInfo) : EMPTY_STRING;
    }

    public static String prefix(ISnapshot snapshot, int objectId, int outbound) throws SnapshotException {
        IObject object = snapshot.getObject(objectId);

        long address = snapshot.mapIdToAddress(outbound);

        StringBuilder s = new StringBuilder(64);

        List<NamedReference> refs = object.getOutboundReferences();
        for (NamedReference reference : refs) {
            if (reference.getObjectAddress() == address) {
                if (s.length() > 0) {
                    s.append(", ");
                }
                s.append(reference.getName());
            }
        }
        return s.toString();
    }

    public static IHeapObjectArgument buildHeapObjectArgument(int[] ids) {
        return new IHeapObjectArgument() {
            @Override
            public int[] getIds(IProgressListener iProgressListener) {
                return ids;
            }

            @Override
            public String getLabel() {
                return "";
            }

            @Override
            public Iterator<int[]> iterator() {
                return new Iterator<int[]>() {

                    boolean hasNext = true;

                    @Override
                    public boolean hasNext() {
                        return hasNext;
                    }

                    @Override
                    public int[] next() {
                        Validate.isTrue(hasNext);
                        hasNext = false;
                        return ids;
                    }
                };
            }
        };
    }

    /**
     * Build or retrieve a cached objectId → node index for a specific children list.
     * Keyed by (tree identity, parentNode identity) so concurrent callers share the same index
     * once it has been built once.
     */
    private static Map<Integer, Object> indexForChildren(AnalysisContext ctx,
                                                          IResultTree tree,
                                                          Object parentNode,
                                                          List<?> elements) {
        AnalysisContext.ChildrenKey key = new AnalysisContext.ChildrenKey(tree, parentNode);
        return ctx.treeChildrenIndex.computeIfAbsent(key, k -> {
            int capacity = elements == null ? 0 : (int) (elements.size() / 0.75f) + 1;
            Map<Integer, Object> index = new HashMap<>(capacity);
            if (elements != null) {
                for (Object node : elements) {
                    IContextObject c = tree.getContext(node);
                    if (c != null) {
                        index.put(c.getObjectId(), node);
                    }
                }
            }
            return index;
        });
    }

    private static Object findObjectInTree(AnalysisContext ctx,
                                            IResultTree tree,
                                            Object parentNode,
                                            List<?> elements,
                                            int targetId) {
        if (elements == null) {
            return null;
        }
        if (ctx != null) {
            return indexForChildren(ctx, tree, parentNode, elements).get(targetId);
        }
        // fallback: linear scan for callers without a context (GCRootPath trees are much smaller)
        for (Object o : elements) {
            IContextObject c = tree.getContext(o);
            if (c != null && c.getObjectId() == targetId) {
                return o;
            }
        }
        return null;
    }

    /**
     * Original signature kept for callers that have no AnalysisContext (e.g. GCRootPath).
     * Uses linear scan — acceptable because those trees are far smaller than the dominator tree.
     */
    public static Object fetchObjectInResultTree(IResultTree tree, int[] idPathInResultTree) {
        return fetchObjectInResultTree(null, tree, idPathInResultTree);
    }

    /**
     * Context-aware variant: uses a cached objectId index for O(1) lookup per level.
     * The roots level of the dominator tree can have millions of entries; indexing eliminates
     * the O(N) scan that previously made every child-expand request take minutes on large heaps.
     */
    public static Object fetchObjectInResultTree(AnalysisContext ctx,
                                                  IResultTree tree,
                                                  int[] idPathInResultTree) {
        if (idPathInResultTree == null || idPathInResultTree.length == 0) {
            return null;
        }

        List<?> roots = tree.getElements();
        Object node = findObjectInTree(ctx, tree, null, roots, idPathInResultTree[0]);

        for (int i = 1; i < idPathInResultTree.length; i++) {
            if (node == null) {
                return null;
            }
            List<?> children = tree.getChildren(node);
            Object parent = node;
            node = findObjectInTree(ctx, tree, parent, children, idPathInResultTree[i]);
        }

        return node;
    }
}
