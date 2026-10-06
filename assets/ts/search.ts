interface SearchPage {
    title: string;
    content: string;
    date: string;
    permalink: string;
    categories: string[];
}

interface SearchResult {
    page: SearchPage;
    score: number;
}

type SearchState = "idle" | "loading" | "ready" | "empty" | "error";
type HistoryAction = "input" | "submit" | "clear";

const escapePattern = (value: string): string => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

class BlogSearch {
    private input: HTMLInputElement;
    private list: HTMLElement;
    private results: HTMLElement;
    private status: HTMLElement;
    private clearButton: HTMLButtonElement;
    private retryButton: HTMLButtonElement;
    private pages: SearchPage[] | null = null;
    private indexPromise: Promise<SearchPage[]> | null = null;
    private timer: number | undefined;
    private composing = false;
    private typingEntryOpen = false;
    private requestID = 0;

    constructor(private form: HTMLFormElement) {
        this.input = form.querySelector(".search-input") as HTMLInputElement;
        this.list = document.querySelector(".search-result-list") as HTMLElement;
        this.results = document.querySelector(".search-results") as HTMLElement;
        this.status = document.querySelector(".search-status") as HTMLElement;
        this.clearButton = form.querySelector(".search-clear") as HTMLButtonElement;
        this.retryButton = document.querySelector(".search-retry") as HTMLButtonElement;

        form.addEventListener("submit", event => {
            event.preventDefault();
            if (this.composing) return;
            this.cancelPendingInput();
            this.search(this.input.value.trim(), "submit");
        });
        this.input.addEventListener("compositionstart", () => {
            this.composing = true;
            this.cancelPendingInput();
        });
        this.input.addEventListener("compositionend", () => {
            this.composing = false;
            this.queueInput();
        });
        this.input.addEventListener("input", event => {
            this.clearButton.hidden = this.input.value.length === 0;
            if (!this.composing && !(event as InputEvent).isComposing) this.queueInput();
        });
        this.clearButton.addEventListener("click", () => {
            this.cancelPendingInput();
            this.input.value = "";
            this.search("", "clear");
            this.input.focus();
        });
        this.retryButton.addEventListener("click", () => {
            this.cancelPendingInput();
            this.search(this.input.value.trim(), "submit");
        });
        window.addEventListener("popstate", () => this.readURL());
        this.readURL();
    }

    private cancelPendingInput(): void {
        window.clearTimeout(this.timer);
        this.timer = undefined;
    }

    private queueInput(): void {
        this.cancelPendingInput();
        this.timer = window.setTimeout(() => {
            const query = this.input.value.trim();
            this.search(query, query ? "input" : "clear");
        }, 180);
    }

    private readURL(): void {
        this.cancelPendingInput();
        this.typingEntryOpen = false;
        this.input.value = new URL(window.location.href).searchParams.get("keyword") || "";
        this.search(this.input.value.trim());
    }

    private updateURL(query: string, action: HistoryAction): void {
        const url = new URL(window.location.href);
        const previous = url.searchParams.get("keyword") || "";
        if (query !== previous) {
            if (query) url.searchParams.set("keyword", query);
            else url.searchParams.delete("keyword");

            // One history entry per typing session; submit and clear keep searches navigable.
            if (action === "input" && this.typingEntryOpen) {
                window.history.replaceState(null, "", url.href);
            } else {
                window.history.pushState(null, "", url.href);
            }
        }
        this.typingEntryOpen = action === "input";
    }

    private setState(state: SearchState, message: string): void {
        this.results.dataset.state = state;
        this.results.setAttribute("aria-busy", String(state === "loading"));
        this.status.textContent = message;
        this.retryButton.hidden = state !== "error";
        this.clearButton.hidden = this.input.value.length === 0;
    }

    private loadIndex(): Promise<SearchPage[]> {
        if (this.pages) return Promise.resolve(this.pages);
        if (this.indexPromise) return this.indexPromise;
        const indexURL = this.form.dataset.indexUrl;
        if (!indexURL) return Promise.reject(new Error("Missing search index URL"));

        this.indexPromise = fetch(indexURL, { credentials: "same-origin" })
            .then(response => {
                if (!response.ok) throw new Error("Search index request failed");
                return response.json();
            })
            .then((data: unknown) => {
                if (!Array.isArray(data)) throw new Error("Invalid search index");
                const pages: SearchPage[] = [];
                for (const entry of data) {
                    if (!entry || typeof entry.title !== "string" || typeof entry.content !== "string" || typeof entry.permalink !== "string" || typeof entry.date !== "string") {
                        throw new Error("Invalid search index entry");
                    }
                    const url = new URL(entry.permalink, window.location.href);
                    if (url.origin !== window.location.origin || !/^https?:$/.test(url.protocol)) {
                        throw new Error("Invalid article URL");
                    }
                    pages.push({
                        title: entry.title,
                        content: entry.content.replace(/\s+/g, " ").trim(),
                        date: entry.date,
                        permalink: url.pathname + url.search + url.hash,
                        categories: Array.isArray(entry.categories) ? entry.categories.filter((category: unknown) => typeof category === "string") : []
                    });
                }
                this.pages = pages;
                return pages;
            })
            .catch(error => {
                // Failed requests are never cached, so both retry and a new query can recover.
                this.indexPromise = null;
                throw error;
            });
        return this.indexPromise;
    }

    private async search(query: string, action?: HistoryAction): Promise<void> {
        if (action) this.updateURL(query, action);
        const requestID = ++this.requestID;
        this.list.replaceChildren();
        if (!query) {
            this.setState("idle", "输入关键词，开始搜索。");
            return;
        }
        this.setState("loading", "正在搜索…");

        try {
            const pages = await this.loadIndex();
            if (requestID !== this.requestID) return;
            const keywords = Array.from(new Set(query.toLowerCase().split(/\s+/).filter(Boolean)));
            const matches: SearchResult[] = [];
            for (const page of pages) {
                const title = page.title.toLowerCase();
                const content = page.content.toLowerCase();
                if (!keywords.every(keyword => title.includes(keyword) || content.includes(keyword))) continue;
                let score = title.includes(query.toLowerCase()) ? 40 : 0;
                for (const keyword of keywords) {
                    if (title.includes(keyword)) score += 20;
                    const count = content.split(keyword).length - 1;
                    score += Math.min(count, 20);
                }
                matches.push({ page, score });
            }
            matches.sort((left, right) => right.score - left.score || right.page.date.localeCompare(left.page.date) || left.page.title.localeCompare(right.page.title, "zh-CN"));
            const fragment = document.createDocumentFragment();
            for (const result of matches) fragment.append(this.renderResult(result.page, keywords));
            this.list.append(fragment);
            this.setState(matches.length ? "ready" : "empty", matches.length ? `找到 ${matches.length} 篇文章` : "没有找到相关文章，试试更短的关键词或换一种表达。");
        } catch (_) {
            if (requestID !== this.requestID) return;
            this.setState("error", "暂时无法加载搜索索引，请重新加载后再试。");
        }
    }

    private highlightedText(text: string, keywords: string[]): DocumentFragment {
        const fragment = document.createDocumentFragment();
        const pattern = new RegExp(keywords.map(escapePattern).sort((left, right) => right.length - left.length).join("|"), "gi");
        let previous = 0;
        let match: RegExpExecArray | null;
        while ((match = pattern.exec(text)) !== null) {
            fragment.append(document.createTextNode(text.slice(previous, match.index)));
            const mark = document.createElement("mark");
            mark.textContent = match[0];
            fragment.append(mark);
            previous = match.index + match[0].length;
        }
        fragment.append(document.createTextNode(text.slice(previous)));
        return fragment;
    }

    private preview(content: string, keywords: string[]): string {
        const firstMatch = keywords.reduce((first, keyword) => {
            const index = content.toLowerCase().indexOf(keyword);
            return index < 0 ? first : Math.min(first, index);
        }, Infinity);
        const start = Number.isFinite(firstMatch) ? Math.max(0, firstMatch - 40) : 0;
        const end = Math.min(content.length, start + 180);
        return (start ? "…" : "") + content.slice(start, end) + (end < content.length ? "…" : "");
    }

    private renderResult(page: SearchPage, keywords: string[]): HTMLElement {
        const article = document.createElement("article");
        article.className = "collection-article-row search-result";
        const meta = document.createElement("div");
        meta.className = "collection-article-meta search-result-meta";
        if (page.categories.length) {
            const category = document.createElement("span");
            category.textContent = page.categories.join(" · ");
            meta.append(category);
        }
        if (/^\d{4}-\d{2}-\d{2}$/.test(page.date)) {
            const time = document.createElement("time");
            time.dateTime = page.date;
            time.textContent = page.date;
            meta.append(time);
        }
        const title = document.createElement("h2");
        title.className = "collection-article-title search-result-title";
        const link = document.createElement("a");
        link.href = page.permalink;
        link.append(this.highlightedText(page.title, keywords));
        title.append(link);
        const summary = document.createElement("p");
        summary.className = "collection-article-summary search-result-summary";
        summary.append(this.highlightedText(this.preview(page.content, keywords), keywords));
        article.append(meta, title, summary);
        return article;
    }
}

const searchForm = document.querySelector("#search-form") as HTMLFormElement | null;
if (searchForm) new BlogSearch(searchForm);
