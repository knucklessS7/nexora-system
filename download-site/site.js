const DOWNLOAD_URL = "https://drive.google.com/uc?export=download&id=16hDuTUyifvMw2uQdFAJEtaPzGmJp_CSS";

const downloadButton = document.querySelector("#downloadButton");
const downloadStatus = document.querySelector("#downloadStatus");
const availability = document.querySelector("#availability");

if (DOWNLOAD_URL) {
  downloadButton.href = DOWNLOAD_URL;
  downloadButton.classList.remove("is-pending");
  downloadButton.removeAttribute("aria-disabled");
  downloadStatus.textContent = "Nexora-Limpa.img.gz · 8,27 GiB";
  availability.textContent = "Download hospedado no Google Drive. Confira o SHA-256 depois de baixar.";
} else {
  downloadButton.addEventListener("click", (event) => event.preventDefault());
}

const copyHash = document.querySelector("#copyHash");
const copyLabel = document.querySelector("#copyLabel");

copyHash.addEventListener("click", async () => {
  const hash = copyHash.querySelector("code").textContent.trim();
  try {
    await navigator.clipboard.writeText(hash);
    copyLabel.textContent = "Copiado";
    setTimeout(() => { copyLabel.textContent = "Copiar"; }, 1800);
  } catch {
    copyLabel.textContent = "Selecione o código";
  }
});
