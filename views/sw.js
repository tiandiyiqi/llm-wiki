/**
 * Service Worker — LLM Wiki PWA
 *
 * 缓存策略：
 * - HTML 页面：Network First（优先网络，离线降级缓存）
 * - CSS/JS/CDN/图片/字体：Cache First（缓存优先，减少请求）
 * - API 请求：Network Only（数据始终从服务器获取）
 */

const CACHE_NAME = 'llm-wiki-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/login.html',
  '/css/responsive.css',
  '/manifest.json',
];

const CDN_CACHE_NAME = 'llm-wiki-cdn-v1';

// Install: 预缓存静态资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Pre-caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate: 清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME && name !== CDN_CACHE_NAME)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch: 路由策略
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API 请求：Network Only
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // 非 GET 请求：不缓存
  if (request.method !== 'GET') {
    return;
  }

  // CDN 资源：Cache First
  if (url.origin !== self.location.origin) {
    event.respondWith(cacheFirst(request, CDN_CACHE_NAME));
    return;
  }

  // 图片资源：Cache First
  if (request.destination === 'image') {
    event.respondWith(cacheFirst(request, CACHE_NAME));
    return;
  }

  // 字体资源：Cache First
  if (request.destination === 'font' || url.pathname.endsWith('.woff2') || url.pathname.endsWith('.woff') || url.pathname.endsWith('.ttf')) {
    event.respondWith(cacheFirst(request, CACHE_NAME));
    return;
  }

  // CSS/JS 静态资源：Cache First
  if (url.pathname.endsWith('.css') || url.pathname.endsWith('.js')) {
    event.respondWith(cacheFirst(request, CACHE_NAME));
    return;
  }

  // HTML 页面：Network First
  if (request.headers.get('accept')?.includes('text/html') || url.pathname.endsWith('.html') || url.pathname === '/') {
    event.respondWith(networkFirst(request));
    return;
  }

  // 其他资源：Network First
  event.respondWith(networkFirst(request));
});

/**
 * Network First 策略
 * 优先从网络获取，失败时从缓存读取
 */
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    // 离线且无缓存：返回简单的离线页面
    if (request.headers.get('accept')?.includes('text/html')) {
      return new Response(
        '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>离线</title></head><body style="display:flex;align-items:center;justify-content:center;min-height:100vh;font-family:system-ui;margin:0;background:#f3f4f6"><div style="text-align:center"><h1 style="color:#667eea">📡 暂无网络</h1><p style="color:#6b7280">请检查网络连接后重试</p><button onclick="location.reload()" style="margin-top:1rem;padding:0.5rem 1.5rem;background:#667eea;color:white;border:none;border-radius:0.5rem;cursor:pointer">重试</button></div></body></html>',
        { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
      );
    }
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Cache First 策略
 * 优先从缓存读取，缓存未命中时从网络获取并缓存
 */
async function cacheFirst(request, cacheName = CACHE_NAME) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}
