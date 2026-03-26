(function () {
  class PromptLabChat {
    constructor() {
      this.form = document.getElementById("chatForm");
      this.chatWindow = document.getElementById("chatWindow");
      this.input = document.getElementById("chatInput");
      this.submitButton = document.getElementById("submitButton");
      this.sendStatus = document.getElementById("sendStatus");
      this.alerts = document.getElementById("clientAlerts");
      this.endpoint = this.form?.dataset.chatEndpoint;
      this.isBusy = false;

      if (!this.form || !this.chatWindow || !this.input || !this.submitButton) {
        return;
      }

      this.bindEvents();
      this.bindDeleteForms();
      this.autoResize();
      this.scrollToBottom(false);
    }

    bindEvents() {
      this.form.addEventListener("submit", (event) => this.handleSubmit(event));
      this.input.addEventListener("keydown", (event) => this.handleKeydown(event));
      this.input.addEventListener("input", () => this.autoResize());
      this.chatWindow.addEventListener("click", (event) => this.handleChatClick(event));
    }

    bindDeleteForms() {
      document.querySelectorAll("[data-chat-delete]").forEach((form) => {
        form.addEventListener("submit", (event) => {
          if (!window.confirm("Excluir este chat?")) {
            event.preventDefault();
          }
        });
      });
    }

    handleKeydown(event) {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();

        if (typeof this.form.requestSubmit === "function") {
          this.form.requestSubmit();
          return;
        }

        this.form.submit();
      }
    }

    async handleSubmit(event) {
      if (!this.endpoint) {
        return;
      }

      event.preventDefault();

      if (this.isBusy) {
        return;
      }

      const message = this.input.value.trim();
      if (!message) {
        this.showAlert("Digite um pedido antes de enviar.", "error");
        return;
      }

      this.clearAlerts();
      this.removeFieldErrors();
      this.removeEmptyState();

      const payload = new FormData(this.form);
      payload.set(this.input.name, message);

      const optimisticUserRow = this.appendMessage({
        role: "user",
        rawContent: message,
        html: this.renderPlainText(message),
      });
      const pendingAssistantRow = this.appendThinkingRow();

      this.input.value = "";
      this.autoResize();
      this.setBusy(true);
      this.setStatus("Pedido enviado. A IA esta reorganizando seu prompt.");
      this.scrollToBottom();

      try {
        const response = await fetch(this.endpoint, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            Accept: "application/json",
          },
          body: payload,
        });

        const data = await this.parseJson(response);
        if (!response.ok || !data.ok) {
          throw new Error(this.resolveErrorMessage(data));
        }

        this.replaceMessageBody(optimisticUserRow, data.user.html, data.user.content, false);
        this.replacePendingRow(pendingAssistantRow, data.assistant.html, data.assistant.content);
        this.updateActiveChatMeta(data.chat);
        this.setStatus("Resposta pronta. Voce pode copiar a mensagem inteira ou um bloco especifico.");
        this.scrollToBottom();
      } catch (error) {
        optimisticUserRow.remove();
        pendingAssistantRow.remove();
        this.input.value = message;
        this.autoResize();
        this.input.focus();
        this.showAlert(
          error instanceof Error ? error.message : "Nao foi possivel enviar a mensagem agora.",
          "error",
        );
        this.setStatus("Falha no envio. Revise a mensagem e tente novamente.");
      } finally {
        this.setBusy(false);
      }
    }

    handleChatClick(event) {
      const actionButton = event.target.closest("[data-action]");
      if (!actionButton) {
        return;
      }

      const action = actionButton.dataset.action;
      if (action === "copy-message") {
        const bubble = actionButton.closest(".message-bubble");
        const content = bubble?.dataset.rawContent || bubble?.innerText || "";
        this.copyText(content, actionButton, "Copiado");
      }

      if (action === "copy-code") {
        const codeElement = actionButton.closest(".code-block")?.querySelector("code");
        const content = codeElement?.textContent || "";
        this.copyText(content, actionButton, "Bloco copiado");
      }
    }

    appendMessage({ role, html, rawContent }) {
      const markup = this.buildMessageMarkup({ role, html, rawContent });
      this.chatWindow.insertAdjacentHTML("beforeend", markup);
      return this.chatWindow.lastElementChild;
    }

    appendThinkingRow() {
      const markup = `
        <div class="message-row assistant is-pending" data-role="assistant">
          <div class="message-meta">
            <span class="message-avatar">PL</span>
            <span class="message-author">PromptLab IA</span>
          </div>
          <div class="message-bubble">
            <div class="typing-shell">
              <span class="typing-label">Pensando no melhor prompt</span>
              <span class="typing-indicator" aria-hidden="true">
                <span></span>
                <span></span>
                <span></span>
              </span>
            </div>
          </div>
        </div>
      `;

      this.chatWindow.insertAdjacentHTML("beforeend", markup);
      return this.chatWindow.lastElementChild;
    }

    replacePendingRow(row, html, rawContent) {
      const replacement = this.createMessageRow({
        role: "assistant",
        html,
        rawContent,
      });

      row.replaceWith(replacement);
      return replacement;
    }

    replaceMessageBody(row, html, rawContent, isAssistant) {
      const bubble = row.querySelector(".message-bubble");
      if (!bubble) {
        return;
      }

      bubble.innerHTML = this.buildBubbleInner(html, isAssistant);
      if (isAssistant) {
        bubble.dataset.rawContent = rawContent;
        bubble.classList.add("rich-response");
      } else {
        bubble.removeAttribute("data-raw-content");
      }
    }

    buildMessageMarkup({ role, html, rawContent }) {
      return this.createMessageRow({ role, html, rawContent }).outerHTML;
    }

    createMessageRow({ role, html, rawContent }) {
      const row = document.createElement("div");
      row.className = `message-row ${role}`;
      row.dataset.role = role;

      row.innerHTML = `
        <div class="message-meta">
          <span class="message-avatar">${role === "user" ? "VO" : "PL"}</span>
          <span class="message-author">${role === "user" ? "Voce" : "PromptLab IA"}</span>
        </div>
        <div class="message-bubble ${role === "assistant" ? "rich-response" : ""}" ${
          role === "assistant" ? `data-raw-content="${this.escapeAttribute(rawContent)}"` : ""
        }>
          ${this.buildBubbleInner(html, role === "assistant")}
        </div>
      `;

      return row;
    }

    buildBubbleInner(html, isAssistant) {
      const copyButton = isAssistant
        ? '<button type="button" class="copy-message-button" data-action="copy-message">Copiar resposta</button>'
        : "";

      return `<div class="message-body">${html}</div>${copyButton}`;
    }

    renderPlainText(text) {
      return `<p>${this.escapeHtml(text).replace(/\n/g, "<br>")}</p>`;
    }

    autoResize() {
      this.input.style.height = "auto";
      this.input.style.height = `${Math.min(this.input.scrollHeight, 224)}px`;
    }

    setBusy(state) {
      this.isBusy = state;
      this.submitButton.disabled = state;
      this.submitButton.querySelector(".submit-label").textContent = state
        ? "Aguardando resposta"
        : "Enviar pedido";
    }

    setStatus(text) {
      if (this.sendStatus) {
        this.sendStatus.textContent = text;
      }
    }

    updateActiveChatMeta(chat) {
      if (!chat) {
        return;
      }

      const titleTarget = document.getElementById("activeChatTitle");
      if (titleTarget) {
        titleTarget.textContent = chat.title;
      }

      const listTitle = document.querySelector(`[data-chat-title="${chat.id}"]`);
      if (listTitle) {
        listTitle.textContent = chat.title;
      }

      const listCount = document.querySelector(`[data-chat-count="${chat.id}"]`);
      if (listCount) {
        listCount.textContent = `${chat.message_count} mensagens`;
      }
    }

    removeEmptyState() {
      const emptyState = document.getElementById("emptyState");
      if (emptyState) {
        emptyState.remove();
      }
    }

    removeFieldErrors() {
      document.querySelector(".field-errors")?.remove();
    }

    showAlert(message, level) {
      if (!this.alerts) {
        return;
      }

      this.alerts.innerHTML = `<div class="alert ${level}">${this.escapeHtml(message)}</div>`;
    }

    clearAlerts() {
      if (!this.alerts) {
        return;
      }

      this.alerts.innerHTML = "";
    }

    async copyText(text, button, successLabel) {
      try {
        await navigator.clipboard.writeText(text);
        this.flashCopiedState(button, successLabel);
      } catch (error) {
        const fallback = document.createElement("textarea");
        fallback.value = text;
        fallback.setAttribute("readonly", "readonly");
        fallback.style.position = "absolute";
        fallback.style.left = "-9999px";
        document.body.appendChild(fallback);
        fallback.select();
        document.execCommand("copy");
        fallback.remove();
        this.flashCopiedState(button, successLabel);
      }
    }

    flashCopiedState(button, successLabel) {
      const originalText = button.textContent;
      button.textContent = successLabel;
      button.classList.add("is-copied");

      window.setTimeout(() => {
        button.textContent = originalText;
        button.classList.remove("is-copied");
      }, 1800);
    }

    scrollToBottom(smooth = true) {
      this.chatWindow.scrollTo({
        top: this.chatWindow.scrollHeight,
        behavior: smooth ? "smooth" : "auto",
      });
    }

    resolveErrorMessage(data) {
      if (!data) {
        return "Nao foi possivel concluir o envio.";
      }

      if (typeof data.error === "string" && data.error.trim()) {
        return data.error;
      }

      if (data.errors?.message?.[0]?.message) {
        return data.errors.message[0].message;
      }

      return "Nao foi possivel concluir o envio.";
    }

    async parseJson(response) {
      try {
        return await response.json();
      } catch (error) {
        return {};
      }
    }

    escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    escapeAttribute(value) {
      return this.escapeHtml(value).replaceAll("\n", "&#10;");
    }
  }

  new PromptLabChat();
})();
