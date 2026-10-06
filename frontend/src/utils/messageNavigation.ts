export function scrollToMessage(messageId: string): boolean {
  const target = document.querySelector<HTMLElement>(
    `[data-message-id="${CSS.escape(messageId)}"]`,
  );

  if (!target) {
    return false;
  }

  target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  target.classList.add('message-highlight');
  window.setTimeout(() => target.classList.remove('message-highlight'), 1600);
  return true;
}
