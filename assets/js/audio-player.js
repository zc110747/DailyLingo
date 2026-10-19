/* ==========================================================================
   DailyLingo — 音频播放器
   使用 HTML5 Audio API 播放真实 WAV 文件；所有显示状态均与真实播放状态同步，
   不存在模拟进度条或伪造播放状态。
   支持：播放/暂停、当前时间、总时长、实时进度、点击与拖动跳转、
        0.75x / 1x / 1.25x 倍速、音量、加载状态、播放结束、加载失败；
        进度条支持键盘左右键（Shift 加速）微调。
        句子高亮：读到哪句就把哪句标粗，拖动/点按跳转后立即跟着走。
   ========================================================================== */

(function () {
  "use strict";

  var RATES = [0.75, 1, 1.25];

  function formatTime(seconds) {
    if (!isFinite(seconds) || seconds < 0) {
      return "--:--";
    }
    var total = Math.floor(seconds);
    var h = Math.floor(total / 3600);
    var m = Math.floor((total % 3600) / 60);
    var s = total % 60;
    var mm = h > 0 ? String(m).padStart(2, "0") : String(m);
    var ss = String(s).padStart(2, "0");
    return h > 0 ? h + ":" + mm + ":" + ss : mm + ":" + ss;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  /* ---------------------------------------------------------------- 句子高亮
     正文里每个句子都是 <span class="sentence" data-start="12.34" data-end="15.67">，
     时间轴由构建脚本从 WAV 的静音结构反推（见 scripts/timeline.py）。

     设计要点：
     * 状态只有「当前句」一个整数，靠 class 切换，不重建 DOM（进度条每 250 ms 触发一次）；
     * 用二分查找定位，几十句的长文也不会拖慢 timeupdate；
     * 快进/后退/拖动都走同一条路径（renderProgress → sync），不需要额外分支。
  */
  function createSentenceTracker(root) {
    var scope = root.closest ? root.closest(".section-article") : null;
    var nodes = Array.prototype.slice.call(
      (scope || document).querySelectorAll("[data-start]")
    );
    if (!nodes.length) {
      return null;
    }

    var starts = nodes.map(function (node) {
      var value = parseFloat(node.getAttribute("data-start"));
      return isFinite(value) ? value : 0;
    });
    var current = -1;

    function indexAt(seconds) {
      var low = 0;
      var high = starts.length - 1;
      var found = 0;
      while (low <= high) {
        var mid = (low + high) >> 1;
        if (starts[mid] <= seconds) {
          found = mid;
          low = mid + 1;
        } else {
          high = mid - 1;
        }
      }
      return found;
    }

    function reveal(node) {
      if (!node.getBoundingClientRect || !node.scrollIntoView) {
        return;
      }
      var rect = node.getBoundingClientRect();
      var viewport = window.innerHeight || document.documentElement.clientHeight || 0;
      if (!viewport) {
        return;
      }
      // 吸顶播放器会遮住正文上沿，可视为「可见区顶部」的额外下移量
      var top = 0;
      if (root.getBoundingClientRect) {
        var player = root.getBoundingClientRect();
        if (player.bottom > 0) {
          top = Math.min(player.bottom, viewport * 0.4);
        }
      }
      if (rect.top >= top + 8 && rect.bottom <= viewport - 8) {
        return;
      }
      var reduce =
        window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      node.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
    }

    function activate(index, shouldReveal) {
      if (index === current || !nodes[index]) {
        return;
      }
      if (current >= 0 && nodes[current]) {
        nodes[current].classList.remove("is-active");
        nodes[current].removeAttribute("aria-current");
      }
      current = index;
      nodes[current].classList.add("is-active");
      nodes[current].setAttribute("aria-current", "true");
      if (shouldReveal) {
        reveal(nodes[current]);
      }
    }

    function sync(seconds) {
      if (!isFinite(seconds) || seconds < 0) {
        return;
      }
      activate(indexAt(seconds), true);
    }

    function hasSelection() {
      var selection = window.getSelection && window.getSelection();
      return !!(selection && String(selection).length);
    }

    return {
      sync: sync,
      /* 点击某句 → 从这句开头播放。句首时间落在停顿里，不会切掉第一个音。 */
      onSelect: function (handler) {
        nodes.forEach(function (node, index) {
          node.addEventListener("click", function () {
            if (hasSelection()) {
              return; // 正在选词/复制，不当作跳转
            }
            handler(starts[index], index);
          });
        });
      }
    };
  }

  function createAudioPlayer(root) {
    var src = root.getAttribute("data-src") || "";
    if (!src) {
      return null;
    }

    var audio = new Audio();
    audio.preload = "metadata";
    audio.src = src;

    var toggle = root.querySelector('[data-action="toggle"]');
    var toggleText = toggle ? toggle.querySelector(".player-toggle-text") : null;
    var track = root.querySelector('[data-action="seek"]');
    var buffered = root.querySelector('[data-role="buffered"]');
    var progress = root.querySelector('[data-role="progress"]');
    var handle = root.querySelector('[data-role="handle"]');
    var currentEl = root.querySelector('[data-role="current"]');
    var durationEl = root.querySelector('[data-role="duration"]');
    var stateEl = root.querySelector('[data-role="state"]');
    var volume = root.querySelector('[data-action="volume"]');
    var rateButtons = Array.prototype.slice.call(root.querySelectorAll("[data-rate]"));

    var duration = 0;
    var seeking = false;
    var failed = false;
    // 播放前不高亮（页面一打开就有一句加粗会让人以为在播放）；
    // 一旦开始播放或用户主动跳转，高亮就接管并一直跟随。
    var armed = false;
    var tracker = createSentenceTracker(root);

    function setState(text, kind) {
      if (!stateEl) {
        return;
      }
      stateEl.textContent = text;
      if (kind) {
        stateEl.setAttribute("data-state", kind);
      } else {
        stateEl.removeAttribute("data-state");
      }
    }

    function setToggleLabel(playing) {
      if (toggleText) {
        toggleText.textContent = playing ? "暂停" : "播放";
      }
      if (toggle) {
        toggle.setAttribute("aria-label", playing ? "暂停" : "播放");
      }
    }

    function renderProgress() {
      var ratio = duration > 0 ? clamp(audio.currentTime / duration, 0, 1) : 0;
      var percent = (ratio * 100).toFixed(3) + "%";
      if (progress) {
        progress.style.width = percent;
      }
      if (handle) {
        handle.style.left = percent;
      }
      if (currentEl) {
        currentEl.textContent = formatTime(audio.currentTime);
      }
      if (track) {
        track.setAttribute("aria-valuemax", String(Math.round(duration)));
        track.setAttribute("aria-valuenow", String(Math.round(audio.currentTime)));
        track.setAttribute("aria-valuetext", formatTime(audio.currentTime) + " / " + formatTime(duration));
      }
      // 所有时间变化（播放 / 拖动 / 左右键 / 点句子）最终都会经过这里，
      // 高亮只需挂在这一个点上，就不会出现「快进后高亮还停在旧句子」。
      if (tracker && armed) {
        tracker.sync(audio.currentTime);
      }
    }

    function fail(message) {
      failed = true;
      setState(message, "error");
      if (toggle) {
        toggle.disabled = true;
        toggle.setAttribute("aria-disabled", "true");
      }
      if (track) {
        track.setAttribute("aria-disabled", "true");
        track.style.cursor = "not-allowed";
      }
      if (durationEl) {
        durationEl.textContent = "--:--";
      }
    }

    function play() {
      if (failed) {
        return;
      }
      var promise = audio.play();
      if (promise && typeof promise.catch === "function") {
        promise.catch(function (err) {
          setToggleLabel(false);
          setState("无法播放：浏览器阻止了自动播放或音频不可用（" + (err && err.name ? err.name : "未知错误") + "）", "error");
        });
      }
    }

    function togglePlay() {
      if (failed) {
        return;
      }
      if (audio.paused) {
        play();
      } else {
        audio.pause();
      }
    }

    function seekBy(delta) {
      if (!duration) {
        return;
      }
      audio.currentTime = clamp(audio.currentTime + delta, 0, duration);
      renderProgress();
    }

    function seekToClientX(clientX) {
      if (!track || !duration) {
        return;
      }
      var rect = track.getBoundingClientRect();
      if (rect.width <= 0) {
        return;
      }
      var ratio = clamp((clientX - rect.left) / rect.width, 0, 1);
      audio.currentTime = ratio * duration;
      renderProgress();
    }

    /* ---------------------------------------------------------- 事件绑定 */

    audio.addEventListener("loadedmetadata", function () {
      duration = isFinite(audio.duration) ? audio.duration : 0;
      if (durationEl) {
        durationEl.textContent = duration > 0 ? formatTime(duration) : "--:--";
      }
      setState(duration > 0 ? "已就绪" : "音频时长不可用");
      renderProgress();
    });

    audio.addEventListener("durationchange", function () {
      duration = isFinite(audio.duration) ? audio.duration : 0;
      if (durationEl && duration > 0) {
        durationEl.textContent = formatTime(duration);
      }
      renderProgress();
    });

    audio.addEventListener("timeupdate", function () {
      armed = true;
      if (!seeking) {
        renderProgress();
      }
    });

    audio.addEventListener("progress", function () {
      if (!buffered || !duration || !audio.buffered || audio.buffered.length === 0) {
        return;
      }
      var end = audio.buffered.end(audio.buffered.length - 1);
      buffered.style.width = (clamp(end / duration, 0, 1) * 100).toFixed(3) + "%";
    });

    audio.addEventListener("play", function () {
      armed = true;
      setToggleLabel(true);
      setState("正在播放");
      renderProgress();
    });

    audio.addEventListener("pause", function () {
      setToggleLabel(false);
      if (!audio.ended) {
        setState("已暂停");
      }
    });

    audio.addEventListener("waiting", function () {
      setState("缓冲中…");
    });

    audio.addEventListener("canplay", function () {
      if (!audio.paused) {
        setState("正在播放");
      }
    });

    audio.addEventListener("ended", function () {
      setToggleLabel(false);
      setState("播放结束");
      renderProgress();
    });

    audio.addEventListener("error", function () {
      fail("音频加载失败：找不到或无法读取 " + src);
    });

    if (toggle) {
      toggle.addEventListener("click", togglePlay);
    }

    rateButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var rate = parseFloat(btn.getAttribute("data-rate"));
        if (!RATES.includes(rate)) {
          return;
        }
        audio.playbackRate = rate;
        rateButtons.forEach(function (other) {
          other.classList.toggle("is-active", other === btn);
          other.setAttribute("aria-pressed", other === btn ? "true" : "false");
        });
      });
      btn.setAttribute("aria-pressed", btn.classList.contains("is-active") ? "true" : "false");
    });

    if (volume) {
      volume.addEventListener("input", function () {
        audio.volume = clamp(parseFloat(volume.value), 0, 1);
      });
      audio.volume = clamp(parseFloat(volume.value), 0, 1);
    }

    if (track) {
      track.addEventListener("pointerdown", function (event) {
        if (failed || !duration) {
          return;
        }
        seeking = true;
        armed = true;
        if (track.setPointerCapture) {
          track.setPointerCapture(event.pointerId);
        }
        seekToClientX(event.clientX);
        event.preventDefault();
      });
      track.addEventListener("pointermove", function (event) {
        if (seeking) {
          seekToClientX(event.clientX);
        }
      });
      var endSeek = function (event) {
        if (!seeking) {
          return;
        }
        seeking = false;
        if (track.releasePointerCapture && event.pointerId !== undefined) {
          try {
            track.releasePointerCapture(event.pointerId);
          } catch (err) {
            /* 指针已释放，忽略 */
          }
        }
      };
      track.addEventListener("pointerup", endSeek);
      track.addEventListener("pointercancel", endSeek);

      track.addEventListener("keydown", function (event) {
        var step = event.shiftKey ? 10 : 5;
        if (event.key === "ArrowLeft") {
          seekBy(-step);
        } else if (event.key === "ArrowRight") {
          seekBy(step);
        } else if (event.key === "Home") {
          audio.currentTime = 0;
          renderProgress();
        } else if (event.key === "End" && duration) {
          audio.currentTime = duration;
          renderProgress();
        } else if (event.key === " " || event.key === "Enter") {
          togglePlay();
        } else {
          return;
        }
        armed = true;
        event.preventDefault();
      });
    }

    if (tracker) {
      tracker.onSelect(function (start) {
        if (failed) {
          return;
        }
        armed = true;
        audio.currentTime = clamp(start, 0, duration || start);
        renderProgress();
        if (audio.paused) {
          play();
        }
      });
    }

    setState("正在加载音频…");
    renderProgress();
    return { audio: audio, togglePlay: togglePlay };
  }

  function init() {
    document.querySelectorAll("[data-player]").forEach(createAudioPlayer);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
