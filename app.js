/*
 * app.js — 法律概念 Wiki 客户端功能
 *
 * 功能:
 *   1. 中文搜索（子串匹配，加载 search-index.json）
 *   2. Sidebar 领域折叠 / 展开
 *   3. 首页搜索
 *   4. 移动端响应式菜单
 *   5. TOC 滚动高亮
 */

(function() {
  'use strict';

  // ─────────────────────────────────────
  // 1. 加载搜索索引
  // ─────────────────────────────────────

  let searchIndex = null;

  function loadSearchIndex() {
    var path = window.location.pathname.endsWith('/index.html') ||
               !window.location.pathname.includes('/')
               ? 'search-index.json'
               : '../search-index.json';

    fetch(path)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        searchIndex = data;
        if (window.onIndexReady) window.onIndexReady();
      })
      .catch(function() {
        console.warn('搜索索引加载失败');
      });
  }

  loadSearchIndex();

  // ─────────────────────────────────────
  // 2. 搜索函数
  // ─────────────────────────────────────

  function doSearch(query) {
    if (!searchIndex || !query) return [];

    var q = query.toLowerCase();
    var results = [];

    for (var i = 0; i < searchIndex.length; i++) {
      var item = searchIndex[i];
      var score = 0;

      // 标题完全匹配
      if (item.t === query) {
        score += 100;
      }
      // 标题包含
      if (item.t.toLowerCase().indexOf(q) >= 0) {
        score += 30;
      }
      // 领域包含
      if (item.d.toLowerCase().indexOf(q) >= 0) {
        score += 15;
      }
      // 关联概念包含
      if (item.r && item.r.length > 0) {
        for (var j = 0; j < item.r.length; j++) {
          if (item.r[j].toLowerCase().indexOf(q) >= 0) {
            score += 8;
            break;
          }
        }
      }
      // 正文包含（基础匹配）
      if (item.b && item.b.toLowerCase().indexOf(q) >= 0) {
        score += 2;
      }

      if (score > 0) {
        results.push({ item: item, score: score });
      }
    }

    // 按得分降序排列
    results.sort(function(a, b) { return b.score - a.score; });

    return results.slice(0, 15); // 最多返回 15 条
  }

  function renderResults(results, container) {
    if (!container) return;

    if (results.length === 0) {
      container.classList.remove('active');
      return;
    }

    var html = '';
    for (var i = 0; i < results.length; i++) {
      var r = results[i].item;
      html += '<div class="search-result-item" onclick="goToResult(\'' +
              r.p.replace(/'/g, "\\'") + '\')">' +
              '<div class="sr-title">' + escapeHtml(r.t) + '</div>' +
              '<div class="sr-domain">' + escapeHtml(r.d) + '</div>' +
              '</div>';
    }

    container.innerHTML = html;
    container.classList.add('active');
  }

  function goToResult(path) {
    // path 来自 search-index.json 的 "p" 字段，如 "article/股东出资责任.html"
    // path 是从根目录计算的相对路径，需要加上当前目录的前缀
    var pathname = window.location.pathname;
    var dir = pathname.substring(0, pathname.lastIndexOf('/') + 1);
    window.location.href = dir + path;
  }

  // 暴露给全局（HTML onclick 需要）
  window.goToResult = goToResult;

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // 关闭搜索下拉
  document.addEventListener('click', function(e) {
    var resultsContainers = document.querySelectorAll('.search-results');
    for (var i = 0; i < resultsContainers.length; i++) {
      var container = resultsContainers[i];
      if (!container.contains(e.target) && e.target.tagName !== 'INPUT') {
        container.classList.remove('active');
      }
    }
  });

  // ─────────────────────────────────────
  // 3. 侧边栏搜索
  // ─────────────────────────────────────

  var sidebarSearch = document.getElementById('sidebar-search');
  var sidebarResults = document.getElementById('sidebar-results');
  var sidebarSearchTimeout = null;

  if (sidebarSearch) {
    sidebarSearch.addEventListener('input', function() {
      clearTimeout(sidebarSearchTimeout);
      var query = this.value.trim();

      if (!query) {
        if (sidebarResults) sidebarResults.classList.remove('active');
        return;
      }

      sidebarSearchTimeout = setTimeout(function() {
        var results = doSearch(query);
        if (sidebarResults) renderResults(results, sidebarResults);
      }, 150);
    });

    sidebarSearch.addEventListener('focus', function() {
      if (this.value.trim() && sidebarResults) {
        var query = this.value.trim();
        var results = doSearch(query);
        if (results.length > 0 && sidebarResults) {
          renderResults(results, sidebarResults);
        }
      }
    });
  }

  // ─────────────────────────────────────
  // 4. 首页搜索
  // ─────────────────────────────────────

  var homeSearch = document.getElementById('home-search');
  var homeResults = document.getElementById('home-results');
  var homeSearchTimeout = null;

  if (homeSearch) {
    homeSearch.addEventListener('input', function() {
      clearTimeout(homeSearchTimeout);
      var query = this.value.trim();

      if (!query) {
        if (homeResults) homeResults.classList.remove('active');
        return;
      }

      homeSearchTimeout = setTimeout(function() {
        var results = doSearch(query);
        if (homeResults) renderResults(results, homeResults);
      }, 150);
    });

    homeSearch.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        var query = this.value.trim();
        if (query) {
          var results = doSearch(query);
          if (results.length > 0) {
            goToResult(results[0].item.p);
          }
        }
      }
    });
  }

  // ─────────────────────────────────────
  // 5. Sidebar 领域折叠 / 展开
  // ─────────────────────────────────────

  window.toggleDomain = function(el) {
    var ul = el.nextElementSibling;
    if (ul && ul.tagName === 'UL') {
      var isHidden = ul.style.display === 'none';
      ul.style.display = isHidden ? 'block' : 'none';
      el.style.background = isHidden ? '#e8e8e8' : 'transparent';
    }
  };

  // ─────────────────────────────────────
  // 6. 移动端 TOC 显示 / 隐藏
  // ─────────────────────────────────────

  window.toggleMobileToc = function() {
    var toc = document.getElementById('article-toc');
    if (toc) {
      toc.classList.toggle('mobile-active');
    }
  };

  // ─────────────────────────────────────
  // 7. 顶部菜单按钮 (移动端)
  // ─────────────────────────────────────

  // 在移动端添加 hamburger 按钮
  (function() {
    if (window.innerWidth > 768) return;

    var nav = document.querySelector('.top-nav');
    if (!nav) return;

    var btn = document.createElement('button');
    btn.className = 'sidebar-trigger';
    btn.innerHTML = '☰';
    btn.style.cssText = 'background:none;border:none;font-size:20px;cursor:pointer;margin-right:12px;color:#333;';

    // 检查是否已经存在
    if (!document.querySelector('.sidebar-trigger')) {
      nav.insertBefore(btn, nav.firstChild);
    }

    btn.addEventListener('click', function() {
      var sidebar = document.querySelector('.sidebar');
      if (sidebar) sidebar.classList.toggle('active');
    });

    // 点击 sidebar 外部关闭
    document.addEventListener('click', function(e) {
      var sidebar = document.querySelector('.sidebar');
      if (!sidebar) return;
      if (sidebar.classList.contains('active') &&
          !sidebar.contains(e.target) &&
          e.target !== btn) {
        sidebar.classList.remove('active');
      }
    });
  })();

  // ─────────────────────────────────────
  // 8. TOC 段落高亮 (IntersectionObserver)
  // ─────────────────────────────────────

  (function() {
    var toc = document.querySelector('.article-toc');
    if (!toc || !window.IntersectionObserver) return;

    var headings = document.querySelectorAll('.article-content h2');
    if (headings.length === 0) return;

    // 给标题添加 id 用于跳转
    for (var i = 0; i < headings.length; i++) {
      if (!headings[i].id) {
        headings[i].id = 'section-' + i;
      }
    }

    // 更新 TOC 链接
    var tocLinks = toc.querySelectorAll('a');
    for (var j = 0; j < tocLinks.length; j++) {
      var href = tocLinks[j].getAttribute('href');
      if (href && href.indexOf('#') === 0) {
        tocLinks[j].addEventListener('click', function(e) {
          e.preventDefault();
          var target = document.querySelector(this.getAttribute('href'));
          if (target) {
            window.scrollTo({
              top: target.offsetTop - 60,
              behavior: 'smooth'
            });
          }
        });
      }
    }

    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        var idx = Array.from(headings).indexOf(entry.target);
        if (idx >= 0 && idx < tocLinks.length) {
          if (entry.isIntersecting) {
            for (var k = 0; k < tocLinks.length; k++) {
              tocLinks[k].style.fontWeight = k === idx ? '600' : 'normal';
            }
          }
        }
      });
    }, { rootMargin: '-60px 0px -70% 0px', threshold: 0 });

    for (var i = 0; i < headings.length; i++) {
      observer.observe(headings[i]);
    }
  })();

  // ─────────────────────────────────────
  // 9. 回到顶部
  // ─────────────────────────────────────

  (function() {
    var footer = document.querySelector('.wiki-footer') ||
                 document.querySelector('.page-nav');
    if (!footer) return;

    var btn = document.createElement('button');
    btn.innerHTML = '↑ 回到顶部';
    btn.className = 'back-to-top';
    btn.style.cssText = [
      'position: fixed; bottom: 32px; right: 24px; z-index: 1000;',
      'background: #fff; color: #3366cc; border: 1px solid #a2a9b1;',
      'border-radius: 4px; padding: 8px 14px; cursor: pointer; font-size: 13px;',
      'display: none; transition: opacity 0.2s;',
      'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'
    ].join('');
    btn.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    document.body.appendChild(btn);

    window.addEventListener('scroll', function() {
      btn.style.display = (window.scrollY > 400) ? 'block' : 'none';
    });
  })();

})();
