"use strict";

(() => {
  const $ = (selector) => document.querySelector(selector);
  const input = $("#text-input");
  const format = new Intl.NumberFormat();
  const names = {
    uppercase: "Uppercase",
    lowercase: "Lowercase",
    titlecase: "Title case",
    slug: "URL slug",
    compact_whitespace: "Clean spaces",
  };
  const MAX_CHARACTERS = 20000;
  const dateFormat = new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  let busy = false;
  let undoText = null;
  let lastAnalysis = null;
  let currentPage = 1;
  let search = "";
  let historyRequest = 0;
  let historyData = null;
  let historyLoading = false;
  let noticeTimer;
  const countCharacters = (text) => [...text].length;

  function announce(message, error = false) {
    clearTimeout(noticeTimer);
    $("#notice-text").textContent = message;
    $("#notice").classList.toggle("error", error);
    $("#notice").hidden = false;
    if (!error)
      noticeTimer = setTimeout(() => {
        $("#notice").hidden = true;
      }, 7000);
  }
  $("#dismiss-notice").addEventListener("click", () => {
    $("#notice").hidden = true;
  });

  function errorMessage(data) {
    if (typeof data?.detail === "string") return data.detail;
    if (!data || typeof data !== "object")
      return "The server could not complete this request. Try again shortly.";
    return (
      Object.values(data).flat().join(" ") ||
      "The request failed. Please try again."
    );
  }

  async function api(path, options = {}) {
    const headers = { Accept: "application/json", ...options.headers };
    if (options.method && options.method !== "GET") {
      const cookie = document.cookie
        .split("; ")
        .find((item) => item.startsWith("csrftoken="));
      headers["X-CSRFToken"] = cookie
        ? decodeURIComponent(cookie.slice(10))
        : "";
      if (options.body) headers["Content-Type"] = "application/json";
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(path, {
        ...options,
        headers,
        credentials: "same-origin",
        cache: "no-store",
        signal: controller.signal,
      });
      if (response.status === 204) return null;
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        if (response.status === 403)
          throw new Error(
            "Your security token expired. Refresh the page and try again.",
          );
        throw new Error(errorMessage(data));
      }
      if (data === null)
        throw new Error(
          "The server returned an unexpected response. Try again shortly.",
        );
      return data;
    } catch (error) {
      if (controller.signal.aborted)
        throw new Error(
          "The request timed out. Check your history before retrying a save.",
        );
      if (error instanceof TypeError)
        throw new Error(
          "Cannot reach the server. Check your connection and try again.",
        );
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }

  function setBusy(value) {
    busy = value;
    document
      .querySelectorAll(
        "#analyze-button,[data-operation],#sample-button,#import-button,#use-result-button,.restore-button",
      )
      .forEach((button) => {
        button.disabled = value;
      });
    $("#undo-button").disabled = value || undoText === null;
    $("#clear-button").disabled = value || !input.value;
    input.readOnly = value;
    $(".analysis-panel").setAttribute("aria-busy", String(value));
    $("#analyze-label").textContent = value ? "Working…" : "Analyze text";
    historyControls();
  }

  function showFieldError(message, focus = false) {
    $("#input-error").textContent = message;
    $("#input-error").hidden = !message;
    input.setAttribute("aria-invalid", String(Boolean(message)));
    if (focus) input.focus();
  }

  function validate() {
    let message = "";
    if (!input.value.trim())
      message = "Enter some text, import a file, or try the example first.";
    else if (countCharacters(input.value) > MAX_CHARACTERS)
      message = "Keep your text within 20,000 characters before continuing.";
    showFieldError(message, Boolean(message));
    return !message;
  }

  function resetAnalysis() {
    lastAnalysis = null;
    $("#export-button").disabled = true;
    [
      "word-count",
      "character-count",
      "compact-count",
      "sentence-count",
      "paragraph-count",
      "unique-count",
      "reading-time",
    ].forEach((id) => {
      $(`#${id}`).textContent = "—";
    });
    $("#analysis-status").textContent = "Ready when you are";
    $("#top-words").replaceChildren();
    $("#frequency-empty").hidden = false;
    $("#transform-output").hidden = true;
    $("#transform-empty").hidden = false;
    document
      .querySelectorAll("[data-operation]")
      .forEach((button) => button.setAttribute("aria-pressed", "false"));
  }

  function inputChanged() {
    const length = countCharacters(input.value);
    $("#input-counter").textContent =
      `${format.format(length)} / 20,000 characters`;
    showFieldError(
      length > MAX_CHARACTERS
        ? "This text is too long. Remove some characters to continue."
        : "",
    );
    $("#clear-button").disabled = busy || !input.value;
    $("#undo-button").disabled = busy || undoText === null;
    resetAnalysis();
    $("#notice").hidden = true;
  }

  function replaceText(text) {
    if (text !== input.value) undoText = input.value;
    input.value = text;
    inputChanged();
    input.focus();
  }

  function showAnalysis(result, status = "Analysis complete") {
    lastAnalysis = { text: input.value, result };
    $("#export-button").disabled = false;
    const fields = {
      "word-count": "word_count",
      "character-count": "character_count",
      "compact-count": "characters_without_whitespace",
      "sentence-count": "sentence_count",
      "paragraph-count": "paragraph_count",
      "unique-count": "unique_word_count",
    };
    for (const [id, key] of Object.entries(fields))
      $(`#${id}`).textContent = format.format(result[key]);
    const seconds = result.reading_time_seconds;
    $("#reading-time").textContent =
      seconds < 60
        ? `${seconds} sec`
        : `${Math.floor(seconds / 60)} min${seconds % 60 ? ` ${seconds % 60} sec` : ""}`;
    $("#analysis-status").textContent = status;
    $("#top-words").replaceChildren();
    $("#frequency-empty").hidden = result.top_words.length > 0;
    for (const item of result.top_words) {
      const li = document.createElement("li");
      const word = document.createElement("span");
      word.className = "frequency-word";
      word.textContent =
        item.word.length > 28 ? `${item.word.slice(0, 28)}…` : item.word;
      if (item.word.length > 28) word.title = item.word.slice(0, 120);
      const bar = document.createElement("meter");
      bar.min = 0;
      bar.max = result.top_words[0].count;
      bar.value = item.count;
      bar.setAttribute("aria-hidden", "true");
      const count = document.createElement("span");
      count.className = "frequency-count";
      count.textContent = format.format(item.count);
      li.append(word, bar, count);
      $("#top-words").append(li);
    }
  }

  async function analyze() {
    if (busy || !validate()) return;
    setBusy(true);
    try {
      const data = await api("/api/text/analyze/", {
        method: "POST",
        body: JSON.stringify({
          text: input.value,
          save: $("#save-analysis").checked,
        }),
      });
      showAnalysis(
        data.result,
        data.saved
          ? "Saved to this browser’s history"
          : "Analyzed without saving",
      );
      announce(
        data.saved
          ? "Analysis complete and saved to your history."
          : "Analysis complete. Your text was not saved.",
      );
      if (data.saved) await loadHistory(1);
    } catch (error) {
      announce(error.message, true);
    } finally {
      setBusy(false);
    }
  }
  $("#analyze-button").addEventListener("click", analyze);
  input.addEventListener("input", inputChanged);
  input.addEventListener("keydown", (event) => {
    if (
      (event.ctrlKey || event.metaKey) &&
      event.key === "Enter" &&
      !event.isComposing &&
      !event.repeat
    ) {
      event.preventDefault();
      analyze();
    }
  });
  $("#shortcut-key").textContent = /Mac|iPhone|iPad/.test(navigator.platform)
    ? "⌘"
    : "Ctrl";
  $("#sample-button").addEventListener("click", () =>
    replaceText(
      "Good writing starts with a clear idea. A clear idea becomes a useful sentence.\n\nTextbench helps you explore your words, find patterns, and give your next draft a little more clarity.",
    ),
  );
  $("#clear-button").addEventListener("click", () => replaceText(""));
  $("#undo-button").addEventListener("click", () => {
    if (undoText === null || busy) return;
    const previous = undoText;
    undoText = input.value;
    input.value = previous;
    inputChanged();
    input.focus();
    announce("Your previous text is back in the editor.");
  });

  $("#import-button").addEventListener("click", () => $("#file-input").click());
  $("#file-input").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file || busy) return;
    setBusy(true);
    try {
      if (!/\.txt$/i.test(file.name))
        throw new Error("Choose a UTF-8 .txt file.");
      if (file.size > 65536)
        throw new Error("Choose a text file smaller than 64 KB.");
      const text = new TextDecoder("utf-8", { fatal: true }).decode(
        await file.arrayBuffer(),
      );
      if (!text.trim())
        throw new Error("This file is empty. Choose a file with some text.");
      if (countCharacters(text) > MAX_CHARACTERS)
        throw new Error(
          "This file exceeds 20,000 characters. Shorten it before importing.",
        );
      replaceText(text);
      announce(
        `Imported ${file.name}. Use Undo to restore the previous draft.`,
      );
    } catch (error) {
      announce(
        error instanceof TypeError
          ? "This file is not valid UTF-8 text. Save it as UTF-8 and try again."
          : error.message,
        true,
      );
    } finally {
      event.target.value = "";
      setBusy(false);
    }
  });

  document.querySelectorAll("[data-operation]").forEach((button) => {
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", async () => {
      if (busy || !validate()) return;
      setBusy(true);
      try {
        const operation = button.dataset.operation;
        const data = await api("/api/text/transform/", {
          method: "POST",
          body: JSON.stringify({ text: input.value, operation }),
        });
        $("#result-text").value = data.result;
        $("#result-label").textContent = names[operation];
        $("#transform-output").hidden = false;
        $("#transform-empty").hidden = true;
        $("#result-help").textContent = data.result
          ? "Transformations are not saved automatically."
          : "No ASCII letters or numbers remain after slug conversion.";
        document
          .querySelectorAll("[data-operation]")
          .forEach((item) =>
            item.setAttribute("aria-pressed", String(item === button)),
          );
        announce(`${names[operation]} result is ready below the tools.`);
      } catch (error) {
        announce(error.message, true);
      } finally {
        setBusy(false);
      }
    });
  });
  $("#use-result-button").addEventListener("click", () => {
    const text = $("#result-text").value;
    if (countCharacters(text) > MAX_CHARACTERS) {
      announce(
        "This result exceeds 20,000 characters. Copy or download it, then shorten it before using it in the editor.",
        true,
      );
      return;
    }
    replaceText(text);
    announce("The result is now in your editor. Undo restores your original.");
  });
  $("#copy-button").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("#result-text").value);
      announce("Result copied to your clipboard.");
    } catch {
      $("#result-text").focus();
      $("#result-text").select();
      announce(
        "Copy is unavailable. The result is selected; use your keyboard to copy it.",
      );
    }
  });
  function download(content, type, filename) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  $("#download-button").addEventListener("click", () =>
    download(
      $("#result-text").value,
      "text/plain;charset=utf-8",
      "textbench-result.txt",
    ),
  );
  $("#export-button").addEventListener("click", () => {
    if (!lastAnalysis || lastAnalysis.text !== input.value) return;
    download(
      JSON.stringify(lastAnalysis, null, 2),
      "application/json;charset=utf-8",
      "textbench-analysis.json",
    );
    announce(
      "Analysis exported. The file includes your text and its statistics.",
    );
  });

  function confirmAction(title, description, label) {
    const dialog = $("#confirm-dialog");
    $("#confirm-title").textContent = title;
    $("#confirm-description").textContent = description;
    $("#confirm-action").textContent = label;
    dialog.returnValue = "cancel";
    return new Promise((resolve) => {
      dialog.addEventListener(
        "close",
        () => resolve(dialog.returnValue === "confirm"),
        { once: true },
      );
      dialog.showModal();
    });
  }

  function historyMessage(title, description) {
    $("#history-message").hidden = false;
    $("#history-message h3").textContent = title;
    $("#history-message p").textContent = description;
  }
  function historyControls() {
    $("#refresh-history").disabled = historyLoading;
    $("#clear-history").disabled =
      busy ||
      historyLoading ||
      !historyData ||
      (!search && historyData.count === 0);
    $("#previous-page").disabled = historyLoading || !historyData?.previous;
    $("#next-page").disabled = historyLoading || !historyData?.next;
    $("#history-list").setAttribute("aria-busy", String(historyLoading));
  }
  async function loadHistory(page = currentPage) {
    const requestNumber = ++historyRequest;
    historyLoading = true;
    historyControls();
    if (!historyData)
      historyMessage(
        "Loading your history…",
        "Retrieving the drafts saved in this browser.",
      );
    try {
      const query = new URLSearchParams({ page: String(page) });
      if (search) query.set("search", search);
      const data = await api(`/api/text/history/?${query}`);
      if (requestNumber !== historyRequest) return;
      currentPage = page;
      historyData = data;
      $("#history-list").replaceChildren();
      $("#history-message").hidden = data.results.length > 0;
      $("#history-count").textContent =
        `${format.format(data.count)} ${search ? "matches" : "saved"}`;
      if (!data.results.length)
        historyMessage(
          search ? "No matching drafts" : "No saved analyses yet",
          search
            ? "Try another word or clear your search to see all saved text."
            : "Select “Save to my history” before analyzing to keep a copy here.",
        );
      for (const item of data.results) {
        const fragment = $("#history-item-template").content.cloneNode(true);
        const preview = fragment.querySelector(".history-preview");
        preview.textContent = item.text.replace(/\s+/g, " ");
        preview.id = `history-preview-${item.id}`;
        fragment.querySelector(".history-details").textContent =
          `${format.format(item.result.word_count)} words / ${dateFormat.format(new Date(item.created_at))}`;
        const restore = fragment.querySelector(".restore-button");
        restore.disabled = busy;
        restore.setAttribute("aria-describedby", preview.id);
        restore.addEventListener("click", () => {
          if (busy) return;
          replaceText(item.text);
          showAnalysis(item.result, "Restored from history");
          announce(
            "Saved text restored. Undo brings back your previous draft.",
          );
        });
        const remove = fragment.querySelector(".delete-button");
        remove.setAttribute("aria-describedby", preview.id);
        remove.addEventListener("click", async () => {
          if (
            !(await confirmAction(
              "Delete this analysis?",
              "This saved copy will be permanently removed. Your current editor text stays as it is.",
              "Delete analysis",
            ))
          )
            return;
          remove.disabled = true;
          try {
            await api(`/api/text/history/${item.id}/`, { method: "DELETE" });
            await loadHistory(
              data.results.length === 1 && page > 1 ? page - 1 : page,
            );
            announce("Saved analysis deleted.");
          } catch (error) {
            announce(error.message, true);
            remove.disabled = false;
          }
        });
        $("#history-list").append(fragment);
      }
      $("#history-pagination").hidden = !data.next && !data.previous;
      $("#page-label").textContent =
        `Page ${page} of ${Math.max(1, Math.ceil(data.count / 6))}`;
    } catch (error) {
      if (requestNumber !== historyRequest) return;
      historyData = null;
      $("#history-list").replaceChildren();
      $("#history-pagination").hidden = true;
      $("#history-count").textContent = "";
      historyMessage(
        "History is unavailable",
        `${error.message} Use Refresh to retry.`,
      );
    } finally {
      if (requestNumber === historyRequest) {
        historyLoading = false;
        historyControls();
      }
    }
  }
  $("#history-search-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const value = $("#history-search").value.trim();
    if (countCharacters(value) > 100) {
      announce("Keep your search within 100 characters.", true);
      return;
    }
    search = value;
    loadHistory(1);
  });
  $("#history-search").addEventListener("search", () => {
    if (!$("#history-search").value) {
      search = "";
      loadHistory(1);
    }
  });
  $("#clear-history").addEventListener("click", async () => {
    if (
      busy ||
      historyLoading ||
      !(await confirmAction(
        "Delete all saved history?",
        "This permanently deletes every saved analysis in this browser’s session, including drafts hidden by a search or another page. Your editor text stays as it is.",
        "Delete all history",
      ))
    )
      return;
    setBusy(true);
    historyLoading = true;
    historyControls();
    try {
      await api("/api/text/history/", { method: "DELETE" });
      await loadHistory(1);
      announce("All saved history for this browser was deleted.");
    } catch (error) {
      historyLoading = false;
      historyControls();
      announce(error.message, true);
    } finally {
      setBusy(false);
    }
  });
  $("#refresh-history").addEventListener("click", () => loadHistory(1));
  $("#previous-page").addEventListener("click", () => {
    if (!historyLoading && historyData?.previous) loadHistory(currentPage - 1);
  });
  $("#next-page").addEventListener("click", () => {
    if (!historyLoading && historyData?.next) loadHistory(currentPage + 1);
  });
  loadHistory(1);
})();
