import { Header } from "./components/header/index.js";
import { PromoSection } from "./components/promo-section/index.js";
import { RegCard } from "./components/reg-card/index.js";
import { LoginCard } from "./components/login-card/index.js";
import { RegVideo } from "./components/reg-video/index.js";

class RegPage {
    constructor(parent) {
        this.parent = parent;
    }

    getPromoRoot() {
        return document.getElementById("promo-section");
    }

    getRegRoot() {
        return document.getElementById("reg-container");
    }

    showLoginCard() {
        const loginCard = new LoginCard(this.getRegRoot(), () => {
            this.showRegCard();
        });
        loginCard.render();
    }

    showRegCard() {
        const regCard = new RegCard(this.getRegRoot(), () => {
            this.showLoginCard();
        });
        regCard.render();
    }

    render() {
        const header = new Header(this.parent);
        header.render();

        const promoSection = new PromoSection(this.parent);
        promoSection.render();

        this.showRegCard();

        const regVideo = new RegVideo(this.getPromoRoot());
        regVideo.render();
    }
}

const root = document.getElementById("root");
const reg_page = new RegPage(root);

reg_page.render();
