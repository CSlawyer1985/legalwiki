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

  function getPageType(pathname) {
    if (pathname.indexOf('/article/') >= 0) return 'page-article';
    if (pathname.indexOf('/domain/') >= 0) return 'page-domain';
    if (pathname.indexOf('/browse') >= 0) return 'page-browse';
    return 'page-home';
  }

  function initPageClasses() {
    if (!document.body) return;
    document.body.classList.add('js-enhanced', getPageType(window.location.pathname));
  }

  initPageClasses();

  // ─────────────────────────────────────
  // 1. 加载搜索索引
  // ─────────────────────────────────────

  let searchIndex = null;

  function loadSearchIndex() {
    var pathname = window.location.pathname;
    // 根据当前页面所在目录决定 search-index.json 的相对路径
    var path = (pathname.indexOf('/article/') >= 0 || pathname.indexOf('/domain/') >= 0)
               ? '../search-index.json'
               : 'search-index.json';

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

  function renderResults(results, container, activeIndex) {
    if (!container) return;

    if (results.length === 0) {
      container.classList.remove('active');
      container.innerHTML = '';
      container.dataset.activeIndex = '-1';
      return;
    }

    var html = '';
    for (var i = 0; i < results.length; i++) {
      var r = results[i].item;
      html += '<div class="search-result-item' +
              (i === activeIndex ? ' is-active' : '') +
              '" data-index="' + i + '" data-path="' + escapeHtml(r.p) +
              '" onclick="goToResult(\'' +
              r.p.replace(/'/g, "\\'") + '\')">' +
              '<div class="sr-title">' + escapeHtml(r.t) + '</div>' +
              '<div class="sr-domain">' + escapeHtml(r.d) + '</div>' +
              '</div>';
    }

    container.innerHTML = html;
    container.classList.add('active');
    container.dataset.activeIndex = String(activeIndex);
  }

  function setActiveResult(container, nextIndex) {
    if (!container || !container.classList.contains('active')) return;

    var items = container.querySelectorAll('.search-result-item');
    if (items.length === 0) return;

    var normalizedIndex = nextIndex;
    if (normalizedIndex < 0) normalizedIndex = items.length - 1;
    if (normalizedIndex >= items.length) normalizedIndex = 0;

    for (var i = 0; i < items.length; i++) {
      items[i].classList.toggle('is-active', i === normalizedIndex);
    }

    container.dataset.activeIndex = String(normalizedIndex);
    items[normalizedIndex].scrollIntoView({ block: 'nearest' });
  }

  function openActiveResult(container) {
    if (!container) return false;

    var activeIndex = parseInt(container.dataset.activeIndex || '-1', 10);
    var activeItem = container.querySelector('.search-result-item.is-active');
    if (!activeItem && activeIndex >= 0) {
      activeItem = container.querySelector('.search-result-item[data-index="' + activeIndex + '"]');
    }
    if (!activeItem) {
      activeItem = container.querySelector('.search-result-item');
    }
    if (!activeItem) return false;

    var path = activeItem.getAttribute('data-path');
    if (!path) return false;

    goToResult(path);
    return true;
  }

  function performSearch(query, container) {
    var results = doSearch(query);
    renderResults(results, container, 0);
    return results;
  }

  function initSearchInput(input, container) {
    if (!input || !container) return;

    var searchTimeout = null;

    input.addEventListener('input', function() {
      clearTimeout(searchTimeout);
      var query = this.value.trim();

      if (!query) {
        container.classList.remove('active');
        container.innerHTML = '';
        container.dataset.activeIndex = '-1';
        return;
      }

      searchTimeout = setTimeout(function() {
        performSearch(query, container);
      }, 120);
    });

    input.addEventListener('focus', function() {
      if (this.value.trim()) {
        performSearch(this.value.trim(), container);
      }
    });

    input.addEventListener('keydown', function(e) {
      var items = container.querySelectorAll('.search-result-item');
      var activeIndex = parseInt(container.dataset.activeIndex || '-1', 10);
      if (isNaN(activeIndex)) activeIndex = -1;

      if (e.key === 'ArrowDown') {
        if (items.length === 0 && this.value.trim()) {
          performSearch(this.value.trim(), container);
          return;
        }
        e.preventDefault();
        setActiveResult(container, activeIndex + 1);
        return;
      }

      if (e.key === 'ArrowUp') {
        if (items.length === 0 && this.value.trim()) {
          performSearch(this.value.trim(), container);
          return;
        }
        e.preventDefault();
        setActiveResult(container, activeIndex <= 0 ? items.length - 1 : activeIndex - 1);
        return;
      }

      if (e.key === 'Enter') {
        var query = this.value.trim();
        if (!query) return;

        e.preventDefault();
        if (!openActiveResult(container)) {
          var results = doSearch(query);
          if (results.length > 0) {
            goToResult(results[0].item.p);
          }
        }
        return;
      }

      if (e.key === 'Escape') {
        container.classList.remove('active');
      }
    });
  }

  function goToResult(path) {
    // path 来自 search-index.json 的 "p" 字段，如 "article/股东出资责任.html"
    // path 是从根目录计算的相对路径，如果当前已在 article/ 下则直接用 path，否则要加上前缀
    var pathname = window.location.pathname;
    if (pathname.indexOf('/article/') >= 0) {
      window.location.href = path;
    } else {
      var dir = pathname.substring(0, pathname.lastIndexOf('/') + 1);
      window.location.href = dir + path;
    }
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
  initSearchInput(sidebarSearch, sidebarResults);

  function setCurrentPageState() {
    var currentPath = window.location.pathname;
    var currentDomainNode = document.querySelector('.domain-title') ||
      document.querySelector('.article-meta .domain-tag');
    var currentDomain = currentDomainNode ? currentDomainNode.textContent.trim() : '';
    var navLinks = document.querySelectorAll('a[href]');

    for (var i = 0; i < navLinks.length; i++) {
      var link = navLinks[i];
      var linkUrl = new URL(link.getAttribute('href'), window.location.href);
      var linkPath = linkUrl.pathname;

      if (linkPath === currentPath) {
        link.classList.add('is-current');
        link.setAttribute('aria-current', 'page');
      }
    }

    var sidebarDomains = document.querySelectorAll('.sidebar-domain');
    for (var j = 0; j < sidebarDomains.length; j++) {
      var domainEl = sidebarDomains[j];
      var domainNameEl = domainEl.querySelector('.sidebar-domain-name');
      var articlesEl = domainEl.nextElementSibling;
      var hasCurrentArticle = !!(articlesEl && articlesEl.querySelector('a.is-current'));
      var isCurrentDomain = !!(domainNameEl && currentDomain &&
        domainNameEl.textContent.trim() === currentDomain);

      if (hasCurrentArticle || isCurrentDomain) {
        domainEl.classList.add('is-open');
        if (isCurrentDomain) {
          domainEl.classList.add('is-current-domain');
        }
        if (articlesEl && articlesEl.tagName === 'UL') {
          articlesEl.style.display = 'block';
        }
      }
    }
  }

  setCurrentPageState();

  function enhanceHomepageSections() {
    if (!document.body.classList.contains('page-home')) return;

    var sectionMap = {
      '高引用概念': 'is-top-cited',
      '桥接概念': 'is-bridge-concepts',
      '最近更新': 'is-recent-updates',
      '浏览全部领域': 'is-domain-index',
      '特色概念': 'is-wiki-intro',
      '快速导航': 'is-quick-nav'
    };

    var sections = document.querySelectorAll('.wp-section');
    for (var i = 0; i < sections.length; i++) {
      var header = sections[i].querySelector('.wp-section-header');
      if (!header) continue;

      var headerText = header.textContent.trim();
      var keys = Object.keys(sectionMap);
      for (var j = 0; j < keys.length; j++) {
        if (headerText.indexOf(keys[j]) >= 0) {
          sections[i].classList.add(sectionMap[keys[j]]);
        }
      }
    }
  }

  enhanceHomepageSections();

  // ─────────────────────────────────────
  // 4. 首页搜索
  // ─────────────────────────────────────

  var homeSearch = document.getElementById('home-search');
  var homeResults = document.getElementById('home-results');
  initSearchInput(homeSearch, homeResults);

  // ─────────────────────────────────────
  // 5. Sidebar 领域折叠 / 展开
  // ─────────────────────────────────────

  window.toggleDomain = function(el) {
    var ul = el.nextElementSibling;
    if (ul && ul.tagName === 'UL') {
      var isHidden = ul.style.display === 'none';
      ul.style.display = isHidden ? 'block' : 'none';
      el.classList.toggle('is-open', isHidden);
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
    if (window.innerWidth > 1024) return;

    var nav = document.querySelector('.top-nav');
    if (!nav) return;

    var btn = document.createElement('button');
    btn.className = 'sidebar-trigger';
    btn.innerHTML = '☰';

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
              tocLinks[k].classList.toggle('is-active', k === idx);
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
  // 9. 文章页内容清理
  // ─────────────────────────────────────

  (function() {
    var pageTitle = document.querySelector('.article-title');
    var content = document.querySelector('.article-content');
    if (!pageTitle || !content) return;

    var firstHeading = content.querySelector(':scope > h1');
    if (firstHeading &&
        firstHeading.textContent.trim() === pageTitle.textContent.trim()) {
      firstHeading.remove();
    }
  })();

  // ─────────────────────────────────────
  // 10. 回到顶部
  // ─────────────────────────────────────

  (function() {
    var footer = document.querySelector('.wiki-footer') ||
                 document.querySelector('.page-nav');
    if (!footer) return;

    var btn = document.createElement('button');
    btn.innerHTML = '↑ 回到顶部';
    btn.className = 'back-to-top';
    btn.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    document.body.appendChild(btn);

    window.addEventListener('scroll', function() {
      btn.style.display = (window.scrollY > 400) ? 'block' : 'none';
    });
  })();

})();
