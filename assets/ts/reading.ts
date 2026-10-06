type ReadingOption = 'focus' | 'guide' | 'bionic';
type ReadingSettings = Record<ReadingOption, boolean>;
const storageKey = 'RicardoReadingPreferences';

function emphasizeWordStarts(content: HTMLElement) {
    const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
            const parent = node.parentElement;
            if (!parent?.closest('p, li') || parent.closest('pre, code, .code-block, a, strong, b, em, kbd, samp, svg, math, mjx-container, h1, h2, h3, h4, h5, h6, table, script, style, .katex, .MathJax, .reader-word-start') || /\$|\\[()[\]A-Za-z]/.test(node.textContent || '')) {
                return NodeFilter.FILTER_REJECT;
            }
            return /[A-Za-z]{3,}/.test(node.textContent || '') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
        }
    });
    const nodes: Text[] = [];
    while (walker.nextNode()) nodes.push(walker.currentNode as Text);
    nodes.forEach(node => {
        const text = node.data;
        const fragment = document.createDocumentFragment();
        const words = /[A-Za-z]{3,}(?:['’][A-Za-z]+)?/g;
        let previousEnd = 0;
        for (const match of text.matchAll(words)) {
            const start = match.index!;
            fragment.appendChild(document.createTextNode(text.slice(previousEnd, start)));
            const word = match[0];
            const prefix = document.createElement('span');
            prefix.className = 'reader-word-start';
            const split = Math.ceil(word.length / 2);
            prefix.textContent = word.slice(0, split);
            fragment.appendChild(prefix);
            fragment.appendChild(document.createTextNode(word.slice(split)));
            previousEnd = start + word.length;
        }
        fragment.appendChild(document.createTextNode(text.slice(previousEnd)));
        node.replaceWith(fragment);
    });
}

export function setupReadingTools() {
    const toolbar = document.querySelector<HTMLElement>('.reading-tools');
    const content = document.querySelector<HTMLElement>('.article-content');
    if (!toolbar || !content) return;
    const buttons = toolbar.querySelectorAll<HTMLButtonElement>('[data-reading-option]');
    const status = toolbar.querySelector<HTMLElement>('.reading-tools__status');
    const settings: ReadingSettings = { focus: false, guide: false, bionic: false };
    try {
        const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
        for (const option of Object.keys(settings) as ReadingOption[]) {
            settings[option] = saved?.[option] === true;
        }
    } catch { /* Reading controls still work when storage is unavailable. */ }

    const paragraphs = Array.from(content.querySelectorAll<HTMLElement>('p, li')).filter(element => {
        if (element.closest('pre, table, .code-block')) return false;
        // Use leaf items, plus an outer item's own paragraphs, so nested lists never overlap.
        if (element.tagName === 'LI') return !element.querySelector('ul, ol');
        const item = element.closest('li');
        return !item || Boolean(item.querySelector('ul, ol'));
    });
    let activeParagraph: HTMLElement | undefined;
    let wordStartsPrepared = false;
    let scrollFrame = 0;
    let keyboardGuide = false;

    function measureToolbar() {
        document.body.style.setProperty('--reading-toolbar-height', `${toolbar!.offsetHeight}px`);
    }

    function highlightParagraph(paragraph?: HTMLElement) {
        if (paragraph === activeParagraph) return;
        activeParagraph?.classList.remove('reader-guide-active');
        activeParagraph = paragraph;
        activeParagraph?.classList.add('reader-guide-active');
    }

    function paragraphAt(target: Element) {
        let paragraph = target.closest<HTMLElement>('p, li');
        while (paragraph && !paragraphs.includes(paragraph)) {
            paragraph = paragraph.parentElement?.closest<HTMLElement>('p, li') || null;
        }
        return paragraph || undefined;
    }

    function visibleParagraph() {
        const target = Math.max(140, window.innerHeight * .5);
        return paragraphs.find(paragraph => {
            const bounds = paragraph.getBoundingClientRect();
            return bounds.bottom > target && bounds.top < window.innerHeight;
        });
    }

    function applySettings() {
        keyboardGuide = false;
        document.body.dataset.readingFocus = String(settings.focus);
        document.body.dataset.readingGuide = String(settings.guide);
        document.body.dataset.readingBionic = String(settings.bionic);
        buttons.forEach(button => {
            button.setAttribute('aria-pressed', String(settings[button.dataset.readingOption as ReadingOption]));
        });
        if (settings.bionic && !wordStartsPrepared) {
            emphasizeWordStarts(content);
            wordStartsPrepared = true;
        } else if (!settings.bionic && wordStartsPrepared) {
            content.querySelectorAll('.reader-word-start').forEach(prefix => {
                const parent = prefix.parentNode;
                prefix.replaceWith(document.createTextNode(prefix.textContent || ''));
                parent?.normalize();
            });
            wordStartsPrepared = false;
        }
        highlightParagraph(settings.guide ? visibleParagraph() : undefined);
        measureToolbar();
        // Layout changes affect the existing theme's heading offsets and ToC indicator.
        window.dispatchEvent(new Event('resize'));
    }

    function saveSettings() {
        try { localStorage.setItem(storageKey, JSON.stringify(settings)); } catch { /* Optional persistence. */ }
    }

    buttons.forEach(button => button.addEventListener('click', () => {
        const option = button.dataset.readingOption as ReadingOption;
        settings[option] = !settings[option];
        applySettings();
        saveSettings();
        if (status) {
            status.textContent = `${button.textContent}${settings[option] ? '已开启' : '已关闭'}`;
            if (option === 'guide' && settings.guide) status.textContent += '，可用 Alt + ↑ / ↓ 切换段落';
        }
    }));

    content.addEventListener('pointerover', event => {
        if (!settings.guide || keyboardGuide) return;
        const paragraph = paragraphAt(event.target as Element);
        if (paragraph) highlightParagraph(paragraph);
    });
    content.addEventListener('pointermove', event => {
        if (!settings.guide || (!event.movementX && !event.movementY)) return;
        keyboardGuide = false;
        const paragraph = paragraphAt(event.target as Element);
        if (paragraph) highlightParagraph(paragraph);
    });
    content.addEventListener('focusin', event => {
        if (!settings.guide) return;
        keyboardGuide = false;
        const paragraph = paragraphAt(event.target as Element);
        if (paragraph) highlightParagraph(paragraph);
    });
    window.addEventListener('scroll', () => {
        if (!settings.guide || keyboardGuide || scrollFrame) return;
        scrollFrame = window.requestAnimationFrame(() => {
            scrollFrame = 0;
            if (settings.guide && !keyboardGuide) highlightParagraph(visibleParagraph());
        });
    }, { passive: true });
    const resumeScrollGuide = () => { keyboardGuide = false; };
    window.addEventListener('wheel', resumeScrollGuide, { passive: true });
    window.addEventListener('touchstart', resumeScrollGuide, { passive: true });
    window.addEventListener('pointerdown', resumeScrollGuide, { passive: true });
    window.addEventListener('resize', measureToolbar);
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && settings.focus) {
            settings.focus = false;
            applySettings();
            saveSettings();
            if (status) status.textContent = '专注模式已关闭';
        }
        if (!settings.guide || !event.altKey || !['ArrowDown', 'ArrowUp'].includes(event.key) || (event.target as Element).closest('input, textarea, select, [contenteditable="true"]')) return;
        event.preventDefault();
        const current = activeParagraph ? paragraphs.indexOf(activeParagraph) : -1;
        const next = current + (event.key === 'ArrowDown' ? 1 : -1);
        const paragraph = paragraphs[Math.max(0, Math.min(paragraphs.length - 1, next))];
        if (!paragraph) return;
        keyboardGuide = true;
        paragraph.scrollIntoView({ block: 'center', behavior: 'instant' as ScrollBehavior });
        highlightParagraph(paragraph);
    });

    toolbar.hidden = false;
    applySettings();
}
