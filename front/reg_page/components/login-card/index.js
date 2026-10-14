export class LoginCard {
    constructor(parent, switchCard) {
        this.parent = parent;
        this.switchCard = switchCard;
    }

    getHTML() {
        return `<div class="login-card">
                <p class="prompt">Введите логин</p>
                <input
                    type="text"
                    class="reg-input-field"
                    placeholder="Логин"
                />
                <p class="prompt">Введите пароль</p>
                <input
                    type="text"
                    class="reg-input-field"
                    placeholder="Пароль"
                />
                <button class="reg-input-button">Войти</button>
                <div class="form-switch">
                    <p>Еще нет аккаунта?</p>
                    <button id="button-switch" class="button-switch">Регистрация</buttom>
                </div>
            </div>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.innerHTML = "";
        this.parent.insertAdjacentHTML("beforeend", html);

        const switchButton = this.parent.querySelector("#button-switch");
        switchButton.addEventListener("click", () => {
            this.switchCard();
        });
    }
}
