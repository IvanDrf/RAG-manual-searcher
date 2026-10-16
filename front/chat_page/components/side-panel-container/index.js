export class SidePanelContainer {
    constructor(parent) {
        this.parent = parent;
    }

    getHTML() {
        return `<div id="side-panel-container" class="side-panel-container">
        </div>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.insertAdjacentHTML("beforeend", html);
    }
}
