export class SidePanelClose {
    constructor(parent, openSidePanel, openChatField, openLibraryField) {
        this.parent = parent;
        this.openSidePanel = openSidePanel;
        this.openChatField = openChatField;
        this.openLibraryField = openLibraryField;
    }

    getHTML() {
        return `<div class="side-panel-close">
            <div class="logo-container">
                <button id="side-panel-button" class="side-panel-close-icon-button">
                    <img
                        class="side-panel-icon"
                        src="./public/media/logo.png"
                        alt="img error"
                    />
                </button>
            </div>
            <button id="chat-field-button" class="side-panel-close-button">
                <img
                    class="side-panel-button-icon"
                    src="./public/media/plus.svg"
                    alt="Error"
                />
            </button>
            <button id="library-field-button" class="side-panel-close-button">
                <img
                    class="side-panel-button-icon"
                    src="./public/media/book.svg"
                    alt="Error"
                />
            </button>
            <div class="side-panel-chat-list">
            </div>
            <div class="side-panel-close-user-button">
                <img
                    class="user-icon"
                    src="./public/media/user-icon.svg"
                    alt=""
                />
            </div>
        </div>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.innerHTML = "";
        this.parent.insertAdjacentHTML("beforeend", html);

        const switchButton = this.parent.querySelector("#side-panel-button");
        switchButton.addEventListener("click", () => {
            this.openSidePanel();
        });

        const openChatFieldButton =
            this.parent.querySelector("#chat-field-button");
        openChatFieldButton.addEventListener("click", () => {
            this.openChatField();
        });

        const openLibraryFieldButton = this.parent.querySelector(
            "#library-field-button",
        );
        openLibraryFieldButton.addEventListener("click", () => {
            this.openLibraryField();
        });
    }
}
