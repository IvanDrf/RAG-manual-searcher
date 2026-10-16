export class LibraryField {
    constructor(parent) {
        this.parent = parent;
    }

    getHTML() {
        return `<div class="library">
                <p class="library-title">Библиотека</p>
                <div class="textbooks-list">
                    <button class="book">
                        <div class="book-image">I</div>
                        <p class="book-title">Математический анализ</p>
                    </button>
                    <button class="book">
                        <div class="book-image">II</div>
                        <p class="book-title">Линейная алгебра</p>
                    </button>
                    <button class="book">
                        <div class="book-image">III</div>
                        <p class="book-title">Теория вероятностей</p>
                    </button>
                    <button class="book">
                        <div class="book-image">IV</div>
                        <p class="book-title">Аналитическая геометрия</p>
                    </button>
                    <button class="book">
                        <div class="book-image">V</div>
                        <p class="book-title">Дискретная математика</p>
                    </button>
                    <button class="book">
                        <div class="book-image">VI</div>
                        <p class="book-title">Дифференциальные уравнения</p>
                    </button>
                </div>
            </div>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.insertAdjacentHTML("beforeend", html);
    }
}
