import "@testing-library/jest-dom/vitest";

// jsdom reflects the `open` attribute on `<dialog>` but doesn't implement
// `showModal`/`close` (see https://github.com/jsdom/jsdom/issues/3294).
// Polyfilled minimally here -- just enough to exercise `LogDialog`'s
// actual open/close behavior in tests -- rather than mocking the dialog
// away in every test file.
if (typeof HTMLDialogElement !== "undefined" && !HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.show = function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
}
