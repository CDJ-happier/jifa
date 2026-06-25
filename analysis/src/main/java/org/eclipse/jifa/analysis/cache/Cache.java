/********************************************************************************
 * Copyright (c) 2021 Contributors to the Eclipse Foundation
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

package org.eclipse.jifa.analysis.cache;

import com.google.common.cache.CacheBuilder;
import org.eclipse.jifa.common.domain.exception.CommonException;

import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;

class Cache {

    private final com.google.common.cache.Cache<CacheKey, Object> cache;

    Cache() {
        cache = CacheBuilder
                .newBuilder()
                .recordStats()
                .expireAfterAccess(240, TimeUnit.MINUTES)
                .build();
    }

    @SuppressWarnings("unchecked")
    <V> V load(CacheKey key, Callable<V> loader) {
        try {
            return (V) cache.get(key, loader);
        } catch (ExecutionException e) {
            throw new CommonException(e);
        }
    }

    static class CacheKey {

        Method method;

        Object[] args;

        CacheKey(Method method, Object[] args) {
            this.method = method;
            this.args = args;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o)
                return true;
            if (o == null || getClass() != o.getClass())
                return false;
            CacheKey cacheKey = (CacheKey) o;
            return method.equals(cacheKey.method) && deepEquals(args, cacheKey.args);
        }

        @Override
        public int hashCode() {
            int hash = method.hashCode();
            return hash * 31 ^ deepHashCode(args);
        }

        // Arrays.equals(Object[]) uses .equals() on each element, which for arrays like int[]
        // is identity comparison.  Use Arrays.deepEquals/deepHashCode instead to correctly
        // handle nested arrays as cache key components.
        private static boolean deepEquals(Object[] a, Object[] b) {
            if (a == b) return true;
            if (a == null || b == null || a.length != b.length) return false;
            for (int i = 0; i < a.length; i++) {
                Object ai = a[i], bi = b[i];
                if (ai == bi) continue;
                if (ai == null || bi == null) return false;
                // Handle primitive arrays (int[], long[], etc.)
                if (ai.getClass().isArray() && bi.getClass().isArray()) {
                    if (!Arrays.deepEquals(new Object[]{ai}, new Object[]{bi})) return false;
                } else if (!ai.equals(bi)) {
                    return false;
                }
            }
            return true;
        }

        private static int deepHashCode(Object[] args) {
            return Arrays.deepHashCode(args);
        }
    }
}
