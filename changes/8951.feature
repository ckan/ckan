feature: Performance improvements by allowing CSRF head meta data to only be activated when CSRF session token is available

* Dynamically include CSRF HEAD Meta when CSRF token is available in user session.
  Allows pages to stay PUBLIC cached for as long as possible.
* A new util JSON interface for CSRF token retrieval for XHR/Fetch calls (protected by CORS)
* A new JS util library for CSRF token retrieval for client side usage
* Allow CSRF subsystem to be fully disabled for true read-only CKAN sites.
