document.addEventListener('DOMContentLoaded', () => {
    const revealZone = document.querySelector('.sidebar-reveal-zone');
    const sidebar = document.querySelector('.sidebar');
    if (!revealZone || !sidebar) return;

    const activeExternalPage = sidebar.querySelector(
        '.nav-link.active[aria-current="page"]'
    );
    if (activeExternalPage && window.innerWidth >= 768) {
        document.body.classList.add('sidebar-hidden');
    }

    const showSidebar = () => document.body.classList.remove('sidebar-hidden');
    revealZone.addEventListener('mouseenter', showSidebar);
    sidebar.addEventListener('focusin', showSidebar);

    document.querySelectorAll('button[data-bs-toggle="tab"]').forEach((tabButton) => {
        tabButton.addEventListener('shown.bs.tab', () => {
            if (window.innerWidth >= 768) document.body.classList.add('sidebar-hidden');
        });
    });
});