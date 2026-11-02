const platform = ReviewFlowExt.detectPlatformFromHost() || "amazon";
ReviewFlowExt.injectToolbar(platform);
ReviewFlowExt.scanPageForReviews(platform);

const observer = new MutationObserver(() => ReviewFlowExt.scanPageForReviews(platform));
observer.observe(document.body, { childList: true, subtree: true });
