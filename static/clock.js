// 7: Clock
function updateClock() {
    const now = new Date();
    const utc = now.toUTCString().slice(17, -4);
    const day = now.toLocaleString("en-US", { weekday: "long", 
                                        month: "long", 
                                        year: "numeric",
                                        day: "2-digit", });
    const local = now.toLocaleDateString([], { 
                                        hour: "2-digit", 
                                        minute: "2-digit" }).slice(10,)
    document.getElementById("clock").textContent = `${day} / ${local} EDT / ${utc} Z `;
};

document.addEventListener("DOMContentLoaded", async () => {

        // Clock — update every second
        updateClock();
        setInterval(updateClock, 1000);

});