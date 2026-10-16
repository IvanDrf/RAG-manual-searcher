export class SidePanelOpen {
    constructor(parent, closeSidePanel, openChatField, openLibraryField) {
        this.parent = parent;
        this.closeSidePanel = closeSidePanel;
        this.openChatField = openChatField;
        this.openLibraryField = openLibraryField;
    }

    getHTML() {
        return `<div class="side-panel-open">
                    <div class="logo-container">
                        <button id="side-panel-button" class="side-panel-open-icon-button">
                            <img
                                class="side-panel-icon"
                                src="./public/media/logo.png"
                                alt="img error"
                            />
                        </button>
                        <p class="side-panel-text">Manual Searcher AI</p>
                    </div>
                    <button id="chat-field-button" class="side-panel-button">
                        <img
                            class="side-panel-button-icon"
                            src="./public/media/plus.svg"
                            alt="Error"
                        />Новый чат
                    </button>
                    <button id="library-field-button" class="side-panel-button">
                        <img
                            class="side-panel-button-icon"
                            src="./public/media/book.svg"
                            alt="Error"
                        />Библиотека
                    </button>
                    <p class="side-panel-chat-list-title">Чаты</p>
                        <div class="side-panel-chat-list">
                            <button class="side-panel-chat-button">Чат 1</button>
                            <button class="side-panel-chat-button">Чат 2</button>
                        </div>
                    <div class="user-button">
                        <img
                            class="user-icon"
                            src="./public/media/user-solid-full.svg"
                            alt=""
                        />
                        <p class="user-name">Username</p>
                    </div>
                </div>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.innerHTML = "";
        this.parent.insertAdjacentHTML("beforeend", html);

        const switchButton = this.parent.querySelector("#side-panel-button");
        switchButton.addEventListener("click", () => {
            this.closeSidePanel();
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
