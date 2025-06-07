(function(templateString) {
    try {
        console.log("🧠 wrap_selected_text invoked");
        console.log("🧠 Selection state:", window.getSelection().toString());
        var selection = window.getSelection();
        if (!selection || selection.rangeCount === 0) {
            console.warn("⚠️ No selection or rangeCount = 0");
            return;
        }
        const anchorNode = selection.anchorNode;
        const inEditable = anchorNode && anchorNode.parentElement && anchorNode.parentElement.isContentEditable;
        if (!inEditable) {
            console.warn("🚫 Selection is not in editable field — skipping insert.");
            return;
        }
        var range = selection.getRangeAt(0);
        var selectedText = range.toString();
        if (templateString.indexOf("{}") === -1) {
            console.warn("⚠️ Template does not contain '{}':", templateString);
        }
        if (selection.rangeCount > 1) {
            console.warn("⚠️ Multiple ranges selected; only first will be used");
        }
        var newHtml;
        if (!selectedText) {
            console.warn("⚠️ No selected text — inserting empty wrapper at caret");
            newHtml = templateString.replace("{}", "");
        } else {
            newHtml = templateString.replace("{}", selectedText);
        }

        console.log("🔧 Inserting HTML:", newHtml);
        // Insert the wrapped HTML into the field
        var container = document.createElement("div");
        container.innerHTML = newHtml;
        var frag = document.createDocumentFragment();
        while (container.firstChild) {
            frag.appendChild(container.firstChild);
        }
        if (frag.firstChild && frag.firstChild.style) {
            frag.firstChild.style.transition = "background 0.4s ease";
            frag.firstChild.style.background = "#ffff99";  // yellow flash
            setTimeout(() => {
                frag.firstChild.style.background = "";
            }, 500);
        }
        range.deleteContents();
        range.insertNode(frag);
        // Restore cursor after the inserted content
        selection.removeAllRanges();
        const newRange = document.createRange();
        newRange.setStartAfter(frag.lastChild || frag);
        newRange.collapse(true);
        selection.addRange(newRange);
    } catch (e) {
        console.error("wrap_selected_text error:", e);
    }
})("TEMPLATE_PLACEHOLDER");