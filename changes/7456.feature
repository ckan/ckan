Re-worked the Feeds generation to match Atom best practices.

`output_feed` method and `CKANFeed` class now accept all 
link ref types that Atom uses (self, enclousre, via, related, alternate).

Added a new feed `feeds/dataset/<id>.atom` that displays a dataset's 
resources as the feed entry items.