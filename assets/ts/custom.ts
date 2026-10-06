import { setupReadingTools } from './reading';

function setupCodeCopyButtons() {
    document.querySelectorAll<HTMLElement>('.article-content .code-block').forEach(block => {
        const highlight = block.querySelector<HTMLElement>('.highlight');
        const code = block.querySelector<HTMLElement>('code[data-lang]');
        if (!highlight || !code) return;

        // Replace Stack's button to keep a single clipboard handler and feedback state.
        const button = document.createElement('button');
        const language = block.querySelector('.code-block__language')?.textContent || '代码';
        const label = language === '代码' ? '复制代码' : `复制 ${language} 代码`;
        button.type = 'button';
        button.className = 'copyCodeButton';
        button.textContent = '复制';
        button.setAttribute('aria-label', label);
        button.setAttribute('aria-live', 'polite');
        const existing = highlight.querySelector('.copyCodeButton');
        if (existing) existing.replaceWith(button);
        else highlight.appendChild(button);

        const numberColumn = block.querySelector('.lntd:first-child');
        if (numberColumn) numberColumn.setAttribute('aria-hidden', 'true');

        let resetTimer: number;
        button.addEventListener('click', async () => {
            window.clearTimeout(resetTimer);
            try {
                const copy = code.cloneNode(true) as HTMLElement;
                copy.querySelectorAll('.ln, .lnt').forEach(number => number.remove());
                await navigator.clipboard.writeText(copy.textContent || '');
                button.textContent = '已复制';
                button.setAttribute('aria-label', '代码已复制');
            } catch {
                button.textContent = '复制失败';
                button.setAttribute('aria-label', '复制失败，请手动选择代码');
            }
            resetTimer = window.setTimeout(() => {
                button.textContent = '复制';
                button.setAttribute('aria-label', label);
            }, 1800);
        });
    });
}

// This deferred script runs after the article DOM is parsed, before image loading finishes.
setupReadingTools();

// Stack adds its buttons in a load timer; initialize after that timer has run.
if (document.readyState === 'complete') {
    window.setTimeout(setupCodeCopyButtons, 0);
} else {
    window.addEventListener('load', () => {
        window.setTimeout(setupCodeCopyButtons, 0);
    }, { once: true });
}
