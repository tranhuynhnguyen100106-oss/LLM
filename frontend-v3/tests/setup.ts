// jsdom không có matchMedia / scrollIntoView / scrollTo; AmbientBackground và AppShell dùng chúng.
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false
    }) as MediaQueryList;
}
Element.prototype.scrollIntoView = Element.prototype.scrollIntoView || (() => undefined);
window.scrollTo = (() => undefined) as typeof window.scrollTo;
