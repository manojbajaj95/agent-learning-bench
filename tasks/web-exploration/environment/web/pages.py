"""Kestrel Depot page tree. Loaded only by root-owned get/post."""

PAGES = {
    "/": {
        "title": "Kestrel Depot",
        "lead": "Field equipment for well sites, flare stacks, and meter runs.",
        "paragraphs": [
            "Kestrel Depot is a private wholesaler. This intranet is the only catalog.",
            "Start at Catalog for SKUs. Use Support for hours and warranty. Use Forms to file work.",
        ],
        "links": [
            ("About", "/about"),
            ("Locations", "/locations"),
            ("Catalog", "/catalog"),
            ("Pricing", "/pricing"),
            ("Support", "/support"),
            ("Policies", "/policies"),
            ("Team", "/team"),
            ("News", "/news"),
            ("Forms", "/forms"),
        ],
    },
    "/about": {
        "title": "About",
        "paragraphs": [
            "Kestrel Depot was founded in 1987 in Coos Bay, Oregon, as a dockside packing house.",
            "The firm now employs 312 people. Inez Calder is president.",
            "The company DUNS number is 08-441-7729.",
            "Headquarters remains in Coos Bay. Branch yards sit in Pueblo, Colorado and Paducah, Kentucky.",
        ],
        "links": [("Locations", "/locations"), ("Team", "/team")],
    },
    "/locations": {
        "title": "Locations",
        "paragraphs": [
            "Three stocking yards. Each yard has its own hours, dock rules, and product limits.",
        ],
        "links": [
            ("Coos Bay (HQ)", "/locations/coos-bay"),
            ("Pueblo", "/locations/pueblo"),
            ("Paducah", "/locations/paducah"),
        ],
    },
    "/locations/coos-bay": {
        "title": "Coos Bay yard",
        "paragraphs": [
            "Address: 14 Harbor Loop, Coos Bay, Oregon.",
            "Hours: Monday-Friday 06:00-18:00. Closed Saturday and Sunday.",
            "Hazmat leaves only from Dock 3.",
            "Same-day outbound cutoff is listed under Policies / Shipping.",
        ],
            "links": [("Shipping policy", "/policies/shipping"), ("Locations", "/locations")],
    },
    "/locations/pueblo": {
        "title": "Pueblo yard",
        "paragraphs": [
            "Address: 880 Mesa Yard, Pueblo, Colorado.",
            "Hours: Monday-Friday 07:00-17:00. Saturday 07:00-12:00. Closed Sunday.",
            "This yard cannot receive igniters. Send igniters to Coos Bay or Paducah.",
            "Yard manager: Tomas Quay.",
        ],
        "links": [("Team", "/team"), ("Locations", "/locations")],
    },
    "/locations/paducah": {
        "title": "Paducah yard",
        "paragraphs": [
            "Address: 21 River Bin Rd, Paducah, Kentucky.",
            "Hours: Monday, Tuesday, Thursday, Friday 07:00-17:00. Closed Wednesday and Sunday.",
            "Saturday is appointment only. Maximum truck length is 48 ft.",
            "Yard manager: Rhea Solt.",
        ],
        "links": [("Team", "/team"), ("Locations", "/locations")],
    },
    "/catalog": {
        "title": "Catalog",
        "paragraphs": [
            "Four families. Open a family, then a SKU. List prices are on the SKU page.",
        ],
        "links": [
            ("Dewpoint sensors", "/catalog/sensors"),
            ("Wellhead gaskets", "/catalog/gaskets"),
            ("Flare igniters", "/catalog/igniters"),
            ("Coalescing filters", "/catalog/filters"),
        ],
    },
    "/catalog/sensors": {
        "title": "Dewpoint sensors",
        "paragraphs": [
            "Used on meter runs. Warranty terms are under Support / Warranty.",
        ],
        "links": [("DP-17 dewpoint probe", "/catalog/sensors/dp-17"), ("Catalog", "/catalog")],
    },
    "/catalog/sensors/dp-17": {
        "title": "DP-17 dewpoint probe",
        "paragraphs": [
            "SKU KD-DP-17. Range -40 to +60 C. List price $418.",
            "Lead time 9 business days from Coos Bay.",
        ],
        "links": [("Sensors", "/catalog/sensors"), ("Request a quote", "/forms/quote")],
    },
    "/catalog/gaskets": {
        "title": "Wellhead gaskets",
        "paragraphs": [
            "Sold in boxes of 12. Returns follow Policies / Returns.",
        ],
        "links": [("WH-220 wellhead gasket", "/catalog/gaskets/wh-220"), ("Catalog", "/catalog")],
    },
    "/catalog/gaskets/wh-220": {
        "title": "WH-220 wellhead gasket",
        "paragraphs": [
            "SKU KD-WH-220. Pressure rating 2200 PSI. Box of 12.",
            "Do not mix lots on one wellhead.",
        ],
        "links": [("Gaskets", "/catalog/gaskets"), ("File an RMA", "/forms/rma")],
    },
    "/catalog/igniters": {
        "title": "Flare igniters",
        "paragraphs": [
            "Spark-window units for flare stacks. Read News for service bulletins before you ship.",
        ],
        "links": [("FS-9 flare igniter", "/catalog/igniters/fs-9"), ("Catalog", "/catalog")],
    },
    "/catalog/igniters/fs-9": {
        "title": "FS-9 flare igniter",
        "paragraphs": [
            "SKU KD-FS-9. Spark window 9 seconds.",
            "Pueblo cannot receive this family. Stock from Coos Bay or Paducah.",
            "Check News for current service bulletins before you pick.",
        ],
        "links": [("Igniters", "/catalog/igniters"), ("News", "/news")],
    },
    "/catalog/filters": {
        "title": "Coalescing filters",
        "paragraphs": [
            "Change intervals are on the SKU page, not on the packing slip.",
        ],
        "links": [("MX-55 coalescing filter", "/catalog/filters/mx-55"), ("Catalog", "/catalog")],
    },
    "/catalog/filters/mx-55": {
        "title": "MX-55 coalescing filter",
        "paragraphs": [
            "SKU KD-MX-55. 55 micron. Change at 400 hours.",
            "No warranty on filter elements.",
        ],
        "links": [("Filters", "/catalog/filters"), ("Open a ticket", "/forms/ticket")],
    },
    "/pricing": {
        "title": "Pricing",
        "paragraphs": [
            "Tier 1 (under $8,000 per year): list price.",
            "Tier 2 ($8,000 to $40,000 per year): 9% off list.",
            "Tier 3 (over $40,000 per year): 16% off list and net-45.",
            "Rush pick fee: $27 per line.",
        ],
        "links": [("Request a quote", "/forms/quote"), ("Credit policy", "/policies/credit")],
    },
    "/support": {
        "title": "Support",
        "paragraphs": [
            "Hours, warranty, and ticket SLOs live on the pages below.",
            "After-hours line: +1-541-555-0194 (Coos Bay dispatch).",
        ],
        "links": [
            ("Hours", "/support/hours"),
            ("Warranty", "/support/warranty"),
            ("FAQ", "/support/faq"),
            ("Open a ticket", "/forms/ticket"),
        ],
    },
    "/support/hours": {
        "title": "Support hours",
        "paragraphs": [
            "Core desk hours: 08:00-16:00 Pacific, every weekday the Coos Bay yard is open.",
            "Pueblo Saturday desk is warehouse-only; there is no phone support on Saturday.",
            "Paducah has no desk on Wednesday.",
        ],
        "links": [("Locations", "/locations"), ("Support", "/support")],
    },
    "/support/warranty": {
        "title": "Warranty",
        "paragraphs": [
            "Sensors: 24 months from ship date.",
            "Gaskets: 90 days.",
            "Igniters: 12 months.",
            "Filter elements: no warranty.",
        ],
        "links": [("File an RMA", "/forms/rma"), ("Support", "/support")],
    },
    "/support/faq": {
        "title": "FAQ",
        "paragraphs": [
            "Demo account for training tickets: KD-4418. PIN 7302.",
            "P1 tickets are for live well shut-in risk. All other faults are P2.",
            "The response SLO for a P1 support ticket is 4 hours. P2 is next business day.",
        ],
        "links": [("Open a ticket", "/forms/ticket"), ("Support", "/support")],
    },
    "/policies": {
        "title": "Policies",
        "paragraphs": ["Shipping, returns, and credit are separate pages."],
        "links": [
            ("Shipping", "/policies/shipping"),
            ("Returns", "/policies/returns"),
            ("Credit", "/policies/credit"),
        ],
    },
    "/policies/shipping": {
        "title": "Shipping",
        "paragraphs": [
            "Same-day shipping cutoff at Coos Bay is 14:45 local.",
            "Hazmat only from Coos Bay Dock 3.",
            "Pueblo will refuse inbound igniters.",
        ],
        "links": [("Coos Bay", "/locations/coos-bay"), ("Policies", "/policies")],
    },
    "/policies/returns": {
        "title": "Returns",
        "paragraphs": [
            "Unused goods may be returned within 21 days of ship date.",
            "Opened packs have a 12% restocking fee.",
            "File an RMA before you ship anything back.",
        ],
        "links": [("File an RMA", "/forms/rma"), ("Policies", "/policies")],
    },
    "/policies/credit": {
        "title": "Credit",
        "paragraphs": [
            "A credit hold is placed at $9,400 past due.",
            "Tier-3 accounts stay on net-45 unless a hold is active.",
        ],
        "links": [("Pricing", "/pricing"), ("Policies", "/policies")],
    },
    "/team": {
        "title": "Team",
        "paragraphs": [
            "President: Inez Calder (Coos Bay).",
            "Pueblo warehouse manager: Tomas Quay.",
            "Paducah warehouse manager: Rhea Solt.",
            "QA lead: N. Pender. Direct QA notes appear only in News.",
        ],
        "links": [("News", "/news"), ("Locations", "/locations")],
    },
    "/news": {
        "title": "News",
        "paragraphs": [
            "Service bulletins and yard notices. Read each post. The home page does not repeat them.",
        ],
        "links": [
            ("FS-9 stop-use bulletin", "/news/fs9-recall"),
            ("Paducah annex", "/news/paducah-annex"),
        ],
    },
    "/news/fs9-recall": {
        "title": "FS-9 stop-use bulletin",
        "paragraphs": [
            "QA lead N. Pender: stop use of FS-9 flare igniters from batch R-FS9-17.",
            "Stop-use date: 12 Mar 2025.",
            "Replacement SKU is KD-FS-9B. Do not mix batches on one stack.",
            "File an RMA with reason recall batch R-FS9-17.",
        ],
        "links": [("FS-9 product page", "/catalog/igniters/fs-9"), ("File an RMA", "/forms/rma")],
    },
    "/news/paducah-annex": {
        "title": "Paducah annex",
        "paragraphs": [
            "A new annex at the Paducah yard opens 4 Nov 2025.",
            "Bin code ANX-P7. Annex phone +1-270-555-0144.",
            "The main Paducah page does not list the annex until it opens.",
        ],
        "links": [("Paducah yard", "/locations/paducah"), ("News", "/news")],
    },
    "/forms": {
        "title": "Forms",
        "paragraphs": [
            "POST field=value pairs with web post. Required fields are on each form page.",
        ],
        "links": [
            ("Contact", "/forms/contact"),
            ("Support ticket", "/forms/ticket"),
            ("Quote", "/forms/quote"),
            ("RMA", "/forms/rma"),
            ("Parts order", "/forms/parts-order"),
        ],
    },
    "/forms/contact": {
        "title": "Contact",
        "paragraphs": ["Sales desk. You will receive a confirmation code."],
        "form": {
            "action": "/forms/contact",
            "fields": [
                {"name": "name", "label": "Name"},
                {"name": "email", "label": "Email"},
                {"name": "topic", "label": "Topic"},
                {"name": "message", "label": "Message", "type": "textarea"},
            ],
        },
        "links": [("Forms", "/forms")],
    },
    "/forms/ticket": {
        "title": "Support ticket",
        "paragraphs": [
            "Priority must be P1 or P2. Use the demo account from the FAQ if you do not have one.",
        ],
        "form": {
            "action": "/forms/ticket",
            "fields": [
                {"name": "sku", "label": "SKU"},
                {"name": "priority", "label": "Priority (P1 or P2)"},
                {"name": "account", "label": "Account"},
                {"name": "description", "label": "Description", "type": "textarea"},
            ],
        },
        "links": [("FAQ", "/support/faq"), ("Forms", "/forms")],
    },
    "/forms/quote": {
        "title": "Quote request",
        "paragraphs": ["ship_site must be Coos Bay, Pueblo, or Paducah."],
        "form": {
            "action": "/forms/quote",
            "fields": [
                {"name": "sku", "label": "SKU"},
                {"name": "qty", "label": "Quantity"},
                {"name": "ship_site", "label": "Ship site"},
            ],
        },
        "links": [("Pricing", "/pricing"), ("Forms", "/forms")],
    },
    "/forms/rma": {
        "title": "RMA",
        "paragraphs": ["Do not ship the part until you have a confirmation code."],
        "form": {
            "action": "/forms/rma",
            "fields": [
                {"name": "sku", "label": "SKU"},
                {"name": "serial", "label": "Serial"},
                {"name": "reason", "label": "Reason", "type": "textarea"},
            ],
        },
        "links": [("Returns", "/policies/returns"), ("Forms", "/forms")],
    },
    "/forms/parts-order": {
        "title": "Parts order",
        "paragraphs": ["Account is required. Demo account is on the FAQ page."],
        "form": {
            "action": "/forms/parts-order",
            "fields": [
                {"name": "sku", "label": "SKU"},
                {"name": "qty", "label": "Quantity"},
                {"name": "account", "label": "Account"},
            ],
        },
        "links": [("Catalog", "/catalog"), ("Forms", "/forms")],
    },
}

FORM_PREFIX = {
    "/forms/contact": "KD-C",
    "/forms/ticket": "KD-T",
    "/forms/quote": "KD-Q",
    "/forms/rma": "KD-R",
    "/forms/parts-order": "KD-O",
}
