import { StrictMode, createElement } from "react";
import { createRoot } from "react-dom/client";
import { AskDocsWidget } from "./askDocs";
import { SHADOW_STYLES } from "../shadowStyles"
import type { WidgetOptions } from "./types";

function mountWidget(
    container : HTMLElement,
    options: WidgetOptions
){
    const host = document.createElement("div")
    host.setAttribute("data-for-widget", "")
    host.setAttribute("data-theme", options.theme ?? "dark")
    host.style.cssText = 'display:block;width:100%;height:100%;'
    container.appendChild(host)

    const shadow = host.attachShadow({mode: 'open'});

    const styleEl = document.createElement('style')
    styleEl.textContent = SHADOW_STYLES             
    shadow.appendChild(styleEl)

    const mountPoint = document.createElement('div')
    mountPoint.style.cssText = 'width:100%;height:100%;'
    shadow.appendChild(mountPoint)

    const root = createRoot(mountPoint)
    root.render(
        createElement(StrictMode, null,
        createElement(AskDocsWidget, { options, shadowHost: host})
        )
    )

    // 6. Cleanup
    return () => {
        root.unmount()
        container.removeChild(host)
    }
}

export default mountWidget