/* ==========================================================================
   DailyLingo — 音频播放器
   使用 HTML5 Audio API 播放真实 WAV 文件；所有显示状态均与真实播放状态同步，
   不存在模拟进度条或伪造播放状态。
   支持：播放/暂停、当前时间、总时长、实时进度、点击与拖动跳转、
        0.75x / 1x / 1.25x 倍速、音量、加载状态、播放结束、加载失败；
        进度条支持键盘左右键（Shift 加速）微调。
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
      setToggleLabel(true);
      setState("正在播放");
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
        event.preventDefault();
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
