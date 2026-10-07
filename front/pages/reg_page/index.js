import { Header } from "../../components/header/index.js";
import { PromoSection } from "../../components/promo-section/index.js";
import { RegCard } from "../../components/reg-card/index.js";
import { RegVideo } from "../../components/reg-video/index.js";

export class RegPage {
    constructor(parent) {
        this.parent = parent;
    }

    getPromoRoot() {
        return document.getElementById("promo-section");
    }

    getRegRoot() {
        return document.getElementById("reg-container");
    }

    render() {
        const header = new Header(this.parent);
        header.render();

        const promoSection = new PromoSection(this.parent);
        promoSection.render();

        const regCard = new RegCard(this.getRegRoot());
        regCard.render();

        const regVideo = new RegVideo(this.getPromoRoot());
        regVideo.render();
    }
}
