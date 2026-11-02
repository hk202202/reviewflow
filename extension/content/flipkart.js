const platform = "flipkart";
ReviewFlowExt.injectToolbar(platform);
ReviewFlowExt.scanPageForReviews(platform);

const observer = new MutationObserver(() => ReviewFlowExt.scanPageForReviews(platform));
observer.observe(document.body, { childList: true, subtree: true });
