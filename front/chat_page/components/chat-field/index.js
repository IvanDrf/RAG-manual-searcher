export class ChatField {
    constructor(parent) {
        this.parent = parent;
    }

    getHTML() {
        return `<div class="chat">
                <div class="chat-feed">
                    <p class="chat-question">В чём хотите разобраться?</p>
                </div>
                <form class="chat-input-field">
                    <div class="chat-input-field-text">
                        <p>Напишите вопрос...</p>
                    </div>
                    <div class="chat-input-field-buttons">
                        <button type="button" class="chat-input-field-send-button">
                            <img src="./public/media/arrow-up.svg" alt="" />
                        </button>
                    </div>
                </form>
            </div>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.insertAdjacentHTML("beforeend", html);
    }
}
