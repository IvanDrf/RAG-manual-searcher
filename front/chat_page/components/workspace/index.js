export class WorkSpace {
    constructor(parent) {
        this.parent = parent;
    }

    getHTML() {
        return `<div id="workspace" class="workspace">
        </div>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.insertAdjacentHTML("beforeend", html);
    }
}
