export class Header {
    constructor(parent) {
        this.parent = parent;
    }

    getHTML() {
        return `<div class="header">
            <div class="logo-container">
                <img
                    src="./public/media/logo.png"
                    class="logo-img"
                    alt="img error"
                />
                <div class="logo-text">Manual-Searcher AI</div>
            </div>
        </div>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.insertAdjacentHTML("beforeend", html);
    }
}
