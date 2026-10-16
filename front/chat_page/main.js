import { SidePanelContainer } from "./components/side-panel-container/index.js";
import { SidePanelClose } from "./components/side-panel-close/index.js";
import { SidePanelOpen } from "./components/side-panel-open/index.js";
import { WorkSpace } from "./components/workspace/index.js";
import { ChatField } from "./components/chat-field/index.js";
import { LibraryField } from "./components/library-field/index.js";

class ChatPage {
    constructor(parent) {
        this.parent = parent;
    }

    getWorkspaceRoot() {
        return document.getElementById("workspace");
    }

    getPanelRoot() {
        return document.getElementById("side-panel-container");
    }

    closeSidePanel() {
        const sidePanelClose = new SidePanelClose(
            this.getPanelRoot(),
            () => {
                this.openSidePanel();
            },
            () => {
                this.openChatField();
            },
            () => {
                this.openLibraryField();
            },
        );
        sidePanelClose.render();
    }

    openSidePanel() {
        const sidePanelOpen = new SidePanelOpen(
            this.getPanelRoot(),
            () => {
                this.closeSidePanel();
            },
            () => {
                this.openChatField();
            },
            () => {
                this.openLibraryField();
            },
        );
        sidePanelOpen.render();
    }

    openChatField() {
        const root = this.getWorkspaceRoot();
        root.innerHTML = "";
        const chatField = new ChatField(this.getWorkspaceRoot());
        chatField.render();
    }

    openLibraryField() {
        const root = this.getWorkspaceRoot();
        root.innerHTML = "";
        const libraryField = new LibraryField(this.getWorkspaceRoot());
        libraryField.render();
    }

    render() {
        const sidePanelContainer = new SidePanelContainer(this.parent);
        sidePanelContainer.render();

        const workspace = new WorkSpace(this.parent);
        workspace.render();

        this.closeSidePanel();

        this.openChatField();
    }
}

const root = document.getElementById("root");
const chatPage = new ChatPage(root);
chatPage.render();
