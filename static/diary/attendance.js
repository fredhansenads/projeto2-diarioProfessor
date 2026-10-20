// Apenas auxilia o preenchimento. A gravação e todas as validações ficam no servidor.
const presentButton = document.querySelector("#fill-present");
if (presentButton) {
  presentButton.hidden = false;
  presentButton.addEventListener("click", () => {
    document.querySelectorAll("[data-absence]").forEach((select) => {
      if (select.value === "") {
        select.value = "0";
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  });
}
