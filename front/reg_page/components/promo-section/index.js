export class PromoSection {
    constructor(parent) {
        this.parent = parent;
    }

    getHTML() {
        return `<div id="promo-section" class="promo-section">
        <div id="reg-container" class="reg-container"></div>
        </div>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.insertAdjacentHTML("beforeend", html);
    }
}
