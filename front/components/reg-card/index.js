export class RegCard {
    constructor(parent) {
        this.parent = parent;
    }

    getHTML() {
        return `<div class="reg-card">
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
                <p class="prompt">Введите пароль еще раз</p>
                <input
                    type="text"
                    class="reg-input-field"
                    placeholder="Пароль"
                />
                <button class="reg-input-button">Зарегистрироваться</button>
                <div class="form-switch">
                    <p>Уже есть аккаунт?</p>
                    <button id="button-switch" class="button-switch">Войти</buttom>
                </div>
            </div>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.insertAdjacentHTML("beforeend", html);
    }
}
