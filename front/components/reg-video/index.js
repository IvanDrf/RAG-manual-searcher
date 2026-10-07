export class RegVideo {
    constructor(parent) {
        this.parent = parent;
    }

    getHTML() {
        return `<video
                src="./public/media/video.mp4"
                autoplay
                muted
                loop
                class="video-conteiner"
            ></video>`;
    }

    render() {
        const html = this.getHTML();
        this.parent.insertAdjacentHTML("beforeend", html);
    }
}
