
	COMMENT ON TYPE box2d IS 'postgis type: A box composed of x min, ymin, xmax, ymax. Often used to return the 2d enclosing box of a geometry.';

	COMMENT ON TYPE box3d IS 'postgis type: A box composed of x min, ymin, zmin, xmax, ymax, zmax. Often used to return the 3d extent of a geometry or collection of geometries.';

	COMMENT ON TYPE geometry IS 'postgis type: Planar spatial data type.';

	COMMENT ON TYPE geometry_dump IS 'postgis type: A spatial datatype with two fields - geom (holding a geometry object) and path[] (a 1-d array holding the position of the geometry within the dumped object.)';

	COMMENT ON TYPE geography IS 'postgis type: Ellipsoidal spatial data type.';

COMMENT ON FUNCTION AddGeometryColumn(varchar , varchar , integer , varchar , integer , boolean ) IS 'args: table_name, column_name, srid, type, dimension, use_typmod=true - Adds a geometry column to an existing table of attributes. By default uses type modifier to define rather than constraints. Pass in false for use_typmod to get old check constraint based behavior';
			
COMMENT ON FUNCTION AddGeometryColumn(varchar , varchar , varchar , integer , varchar , integer , boolean ) IS 'args: schema_name, table_name, column_name, srid, type, dimension, use_typmod=true - Adds a geometry column to an existing table of attributes. By default uses type modifier to define rather than constraints. Pass in false for use_typmod to get old check constraint based behavior';
			
COMMENT ON FUNCTION AddGeometryColumn(varchar , varchar , varchar , varchar , integer , varchar , integer , boolean ) IS 'args: catalog_name, schema_name, table_name, column_name, srid, type, dimension, use_typmod=true - Adds a geometry column to an existing table of attributes. By default uses type modifier to define rather than constraints. Pass in false for use_typmod to get old check constraint based behavior';
			
COMMENT ON FUNCTION DropGeometryColumn(varchar , varchar ) IS 'args: table_name, column_name - Removes a geometry column from a spatial table.';
			
COMMENT ON FUNCTION DropGeometryColumn(varchar , varchar , varchar ) IS 'args: schema_name, table_name, column_name - Removes a geometry column from a spatial table.';
			
COMMENT ON FUNCTION DropGeometryColumn(varchar , varchar , varchar , varchar ) IS 'args: catalog_name, schema_name, table_name, column_name - Removes a geometry column from a spatial table.';
			
COMMENT ON FUNCTION DropGeometryTable(varchar ) IS 'args: table_name - Drops a table and all its references in geometry_columns.';
			
COMMENT ON FUNCTION DropGeometryTable(varchar , varchar ) IS 'args: schema_name, table_name - Drops a table and all its references in geometry_columns.';
			
COMMENT ON FUNCTION DropGeometryTable(varchar , varchar , varchar ) IS 'args: catalog_name, schema_name, table_name - Drops a table and all its references in geometry_columns.';
			
COMMENT ON FUNCTION PostGIS_Full_Version() IS 'Reports full postgis version and build configuration infos.';
			
COMMENT ON FUNCTION PostGIS_GEOS_Version() IS 'Returns the version number of the GEOS library.';
			
COMMENT ON FUNCTION PostGIS_LibXML_Version() IS 'Returns the version number of the libxml2 library.';
			
COMMENT ON FUNCTION PostGIS_Lib_Build_Date() IS 'Returns build date of the PostGIS library.';
			
COMMENT ON FUNCTION PostGIS_Lib_Version() IS 'Returns the version number of the PostGIS library.';
			
COMMENT ON FUNCTION PostGIS_PROJ_Version() IS 'Returns the version number of the PROJ4 library.';
			
COMMENT ON FUNCTION PostGIS_Scripts_Build_Date() IS 'Returns build date of the PostGIS scripts.';
			
COMMENT ON FUNCTION PostGIS_Scripts_Installed() IS 'Returns version of the postgis scripts installed in this database.';
			
COMMENT ON FUNCTION PostGIS_Scripts_Released() IS 'Returns the version number of the postgis.sql script released with the installed postgis lib.';
			
COMMENT ON FUNCTION PostGIS_Version() IS 'Returns PostGIS version number and compile-time options.';
			
COMMENT ON FUNCTION Populate_Geometry_Columns(boolean ) IS 'args: use_typmod=true - Ensures geometry columns are defined with type modifiers or have appropriate spatial constraints This ensures they will be registered correctly in geometry_columns view. By default will convert all geometry columns with no type modifier to ones with type modifiers. To get old behavior set use_typmod=false';
			
COMMENT ON FUNCTION Populate_Geometry_Columns(oid, boolean ) IS 'args: relation_oid, use_typmod=true - Ensures geometry columns are defined with type modifiers or have appropriate spatial constraints This ensures they will be registered correctly in geometry_columns view. By default will convert all geometry columns with no type modifier to ones with type modifiers. To get old behavior set use_typmod=false';
			
COMMENT ON FUNCTION UpdateGeometrySRID(varchar , varchar , integer ) IS 'args: table_name, column_name, srid - Updates the SRID of all features in a geometry column, geometry_columns metadata and srid. If it was enforced with constraints, the constraints will be updated with new srid constraint. If the old was enforced by type definition, the type definition will be changed.';
			
COMMENT ON FUNCTION UpdateGeometrySRID(varchar , varchar , varchar , integer ) IS 'args: schema_name, table_name, column_name, srid - Updates the SRID of all features in a geometry column, geometry_columns metadata and srid. If it was enforced with constraints, the constraints will be updated with new srid constraint. If the old was enforced by type definition, the type definition will be changed.';
			
COMMENT ON FUNCTION UpdateGeometrySRID(varchar , varchar , varchar , varchar , integer ) IS 'args: catalog_name, schema_name, table_name, column_name, srid - Updates the SRID of all features in a geometry column, geometry_columns metadata and srid. If it was enforced with constraints, the constraints will be updated with new srid constraint. If the old was enforced by type definition, the type definition will be changed.';
			
COMMENT ON FUNCTION ST_BdPolyFromText(text , integer ) IS 'args: WKT, srid - Construct a Polygon given an arbitrary collection of closed linestrings as a MultiLineString Well-Known text representation.';
			
COMMENT ON FUNCTION ST_BdMPolyFromText(text , integer ) IS 'args: WKT, srid - Construct a MultiPolygon given an arbitrary collection of closed linestrings as a MultiLineString text representation Well-Known text representation.';
			
COMMENT ON FUNCTION ST_Box2dFromGeoHash(text , integer ) IS 'args: geohash, precision=full_precision_of_geohash - Return a BOX2D from a GeoHash string.';
			
COMMENT ON FUNCTION ST_GeogFromText(text ) IS 'args: EWKT - Return a specified geography value from Well-Known Text representation or extended (WKT).';
			
COMMENT ON FUNCTION ST_GeographyFromText(text ) IS 'args: EWKT - Return a specified geography value from Well-Known Text representation or extended (WKT).';
			
COMMENT ON FUNCTION ST_GeogFromWKB(bytea ) IS 'args: geom - Creates a geography instance from a Well-Known Binary geometry representation (WKB) or extended Well Known Binary (EWKB).';
			
COMMENT ON FUNCTION ST_GeomCollFromText(text , integer ) IS 'args: WKT, srid - Makes a collection Geometry from collection WKT with the given SRID. If SRID is not give, it defaults to 0.';
			
COMMENT ON FUNCTION ST_GeomCollFromText(text ) IS 'args: WKT - Makes a collection Geometry from collection WKT with the given SRID. If SRID is not give, it defaults to 0.';
			
COMMENT ON FUNCTION ST_GeomFromEWKB(bytea ) IS 'args: EWKB - Return a specified ST_Geometry value from Extended Well-Known Binary representation (EWKB).';
			
COMMENT ON FUNCTION ST_GeomFromEWKT(text ) IS 'args: EWKT - Return a specified ST_Geometry value from Extended Well-Known Text representation (EWKT).';
			
COMMENT ON FUNCTION ST_GeometryFromText(text ) IS 'args: WKT - Return a specified ST_Geometry value from Well-Known Text representation (WKT). This is an alias name for ST_GeomFromText';
			
COMMENT ON FUNCTION ST_GeometryFromText(text , integer ) IS 'args: WKT, srid - Return a specified ST_Geometry value from Well-Known Text representation (WKT). This is an alias name for ST_GeomFromText';
			
COMMENT ON FUNCTION ST_GeomFromGeoHash(text , integer ) IS 'args: geohash, precision=full_precision_of_geohash - Return a geometry from a GeoHash string.';
			
COMMENT ON FUNCTION ST_GeomFromGML(text ) IS 'args: geomgml - Takes as input GML representation of geometry and outputs a PostGIS geometry object';
			
COMMENT ON FUNCTION ST_GeomFromGML(text , integer ) IS 'args: geomgml, srid - Takes as input GML representation of geometry and outputs a PostGIS geometry object';
			
COMMENT ON FUNCTION ST_GeomFromGeoJSON(text ) IS 'args: geomjson - Takes as input a geojson representation of a geometry and outputs a PostGIS geometry object';
			
COMMENT ON FUNCTION ST_GeomFromKML(text ) IS 'args: geomkml - Takes as input KML representation of geometry and outputs a PostGIS geometry object';
			
COMMENT ON FUNCTION ST_GMLToSQL(text ) IS 'args: geomgml - Return a specified ST_Geometry value from GML representation. This is an alias name for ST_GeomFromGML';
			
COMMENT ON FUNCTION ST_GMLToSQL(text , integer ) IS 'args: geomgml, srid - Return a specified ST_Geometry value from GML representation. This is an alias name for ST_GeomFromGML';
			
COMMENT ON FUNCTION ST_GeomFromText(text ) IS 'args: WKT - Return a specified ST_Geometry value from Well-Known Text representation (WKT).';
			
COMMENT ON FUNCTION ST_GeomFromText(text , integer ) IS 'args: WKT, srid - Return a specified ST_Geometry value from Well-Known Text representation (WKT).';
			
COMMENT ON FUNCTION ST_GeomFromWKB(bytea ) IS 'args: geom - Creates a geometry instance from a Well-Known Binary geometry representation (WKB) and optional SRID.';
			
COMMENT ON FUNCTION ST_GeomFromWKB(bytea , integer ) IS 'args: geom, srid - Creates a geometry instance from a Well-Known Binary geometry representation (WKB) and optional SRID.';
			
COMMENT ON FUNCTION ST_LineFromMultiPoint(geometry ) IS 'args: aMultiPoint - Creates a LineString from a MultiPoint geometry.';
			
COMMENT ON FUNCTION ST_LineFromText(text ) IS 'args: WKT - Makes a Geometry from WKT representation with the given SRID. If SRID is not given, it defaults to 0.';
			
COMMENT ON FUNCTION ST_LineFromText(text , integer ) IS 'args: WKT, srid - Makes a Geometry from WKT representation with the given SRID. If SRID is not given, it defaults to 0.';
			
COMMENT ON FUNCTION ST_LineFromWKB(bytea ) IS 'args: WKB - Makes a LINESTRING from WKB with the given SRID';
			
COMMENT ON FUNCTION ST_LineFromWKB(bytea , integer ) IS 'args: WKB, srid - Makes a LINESTRING from WKB with the given SRID';
			
COMMENT ON FUNCTION ST_LinestringFromWKB(bytea ) IS 'args: WKB - Makes a geometry from WKB with the given SRID.';
			
COMMENT ON FUNCTION ST_LinestringFromWKB(bytea , integer ) IS 'args: WKB, srid - Makes a geometry from WKB with the given SRID.';
			
COMMENT ON FUNCTION ST_MakeBox2D(geometry , geometry ) IS 'args: pointLowLeft, pointUpRight - Creates a BOX2D defined by the given point geometries.';
			
COMMENT ON FUNCTION ST_3DMakeBox(geometry , geometry ) IS 'args: point3DLowLeftBottom, point3DUpRightTop - Creates a BOX3D defined by the given 3d point geometries.';
			
COMMENT ON AGGREGATE ST_MakeLine(geometry) IS 'args: geoms - Creates a Linestring from point or line geometries.';
			
COMMENT ON FUNCTION ST_MakeLine(geometry, geometry) IS 'args: geom1, geom2 - Creates a Linestring from point or line geometries.';
			
COMMENT ON FUNCTION ST_MakeLine(geometry[]) IS 'args: geoms_array - Creates a Linestring from point or line geometries.';
			
COMMENT ON FUNCTION ST_MakeEnvelope(double precision, double precision, double precision, double precision, integer ) IS 'args: xmin, ymin, xmax, ymax, srid=unknown - Creates a rectangular Polygon formed from the given minimums and maximums. Input values must be in SRS specified by the SRID.';
			
COMMENT ON FUNCTION ST_MakePolygon(geometry) IS 'args: linestring - Creates a Polygon formed by the given shell. Input geometries must be closed LINESTRINGS.';
			
COMMENT ON FUNCTION ST_MakePolygon(geometry, geometry[]) IS 'args: outerlinestring, interiorlinestrings - Creates a Polygon formed by the given shell. Input geometries must be closed LINESTRINGS.';
			
COMMENT ON FUNCTION ST_MakePoint(double precision, double precision) IS 'args: x, y - Creates a 2D,3DZ or 4D point geometry.';
			
COMMENT ON FUNCTION ST_MakePoint(double precision, double precision, double precision) IS 'args: x, y, z - Creates a 2D,3DZ or 4D point geometry.';
			
COMMENT ON FUNCTION ST_MakePoint(double precision, double precision, double precision, double precision) IS 'args: x, y, z, m - Creates a 2D,3DZ or 4D point geometry.';
			
COMMENT ON FUNCTION ST_MakePointM(float, float, float) IS 'args: x, y, m - Creates a point geometry with an x y and m coordinate.';
			
COMMENT ON FUNCTION ST_MLineFromText(text , integer ) IS 'args: WKT, srid - Return a specified ST_MultiLineString value from WKT representation.';
			
COMMENT ON FUNCTION ST_MLineFromText(text ) IS 'args: WKT - Return a specified ST_MultiLineString value from WKT representation.';
			
COMMENT ON FUNCTION ST_MPointFromText(text , integer ) IS 'args: WKT, srid - Makes a Geometry from WKT with the given SRID. If SRID is not give, it defaults to 0.';
			
COMMENT ON FUNCTION ST_MPointFromText(text ) IS 'args: WKT - Makes a Geometry from WKT with the given SRID. If SRID is not give, it defaults to 0.';
			
COMMENT ON FUNCTION ST_MPolyFromText(text , integer ) IS 'args: WKT, srid - Makes a MultiPolygon Geometry from WKT with the given SRID. If SRID is not give, it defaults to 0.';
			
COMMENT ON FUNCTION ST_MPolyFromText(text ) IS 'args: WKT - Makes a MultiPolygon Geometry from WKT with the given SRID. If SRID is not give, it defaults to 0.';
			
COMMENT ON FUNCTION ST_Point(float , float ) IS 'args: x_lon, y_lat - Returns an ST_Point with the given coordinate values. OGC alias for ST_MakePoint.';
			
COMMENT ON FUNCTION ST_PointFromGeoHash(text , integer ) IS 'args: geohash, precision=full_precision_of_geohash - Return a point from a GeoHash string.';
			
COMMENT ON FUNCTION ST_PointFromText(text ) IS 'args: WKT - Makes a point Geometry from WKT with the given SRID. If SRID is not given, it defaults to unknown.';
			
COMMENT ON FUNCTION ST_PointFromText(text , integer ) IS 'args: WKT, srid - Makes a point Geometry from WKT with the given SRID. If SRID is not given, it defaults to unknown.';
			
COMMENT ON FUNCTION ST_GeomFromWKB(bytea ) IS 'args: geom - Makes a geometry from WKB with the given SRID';
			
COMMENT ON FUNCTION ST_GeomFromWKB(bytea , integer ) IS 'args: geom, srid - Makes a geometry from WKB with the given SRID';
			
COMMENT ON FUNCTION ST_Polygon(geometry , integer ) IS 'args: aLineString, srid - Returns a polygon built from the specified linestring and SRID.';
			
COMMENT ON FUNCTION ST_PolygonFromText(text ) IS 'args: WKT - Makes a Geometry from WKT with the given SRID. If SRID is not give, it defaults to 0.';
			
COMMENT ON FUNCTION ST_PolygonFromText(text , integer ) IS 'args: WKT, srid - Makes a Geometry from WKT with the given SRID. If SRID is not give, it defaults to 0.';
			
COMMENT ON FUNCTION ST_WKBToSQL(bytea ) IS 'args: WKB - Return a specified ST_Geometry value from Well-Known Binary representation (WKB). This is an alias name for ST_GeomFromWKB that takes no srid';
			
COMMENT ON FUNCTION ST_WKTToSQL(text ) IS 'args: WKT - Return a specified ST_Geometry value from Well-Known Text representation (WKT). This is an alias name for ST_GeomFromText';
			
COMMENT ON FUNCTION GeometryType(geometry ) IS 'args: geomA - Returns the type of the geometry as a string. Eg: LINESTRING, POLYGON, MULTIPOINT, etc.';
			
COMMENT ON FUNCTION ST_Boundary(geometry ) IS 'args: geomA - Returns the closure of the combinatorial boundary of this Geometry.';
			
COMMENT ON FUNCTION ST_CoordDim(geometry ) IS 'args: geomA - Return the coordinate dimension of the ST_Geometry value.';
			
COMMENT ON FUNCTION ST_Dimension(geometry ) IS 'args: g - The inherent dimension of this Geometry object, which must be less than or equal to the coordinate dimension.';
			
COMMENT ON FUNCTION ST_EndPoint(geometry ) IS 'args: g - Returns the last point of a LINESTRING geometry as a POINT.';
			
COMMENT ON FUNCTION ST_Envelope(geometry ) IS 'args: g1 - Returns a geometry representing the double precision (float8) bounding box of the supplied geometry.';
			
COMMENT ON FUNCTION ST_ExteriorRing(geometry ) IS 'args: a_polygon - Returns a line string representing the exterior ring of the POLYGON geometry. Return NULL if the geometry is not a polygon. Will not work with MULTIPOLYGON';
			
COMMENT ON FUNCTION ST_GeometryN(geometry , integer ) IS 'args: geomA, n - Return the 1-based Nth geometry if the geometry is a GEOMETRYCOLLECTION, (MULTI)POINT, (MULTI)LINESTRING, MULTICURVE or (MULTI)POLYGON, POLYHEDRALSURFACE Otherwise, return NULL.';
			
COMMENT ON FUNCTION ST_GeometryType(geometry ) IS 'args: g1 - Return the geometry type of the ST_Geometry value.';
			
COMMENT ON FUNCTION ST_InteriorRingN(geometry , integer ) IS 'args: a_polygon, n - Return the Nth interior linestring ring of the polygon geometry. Return NULL if the geometry is not a polygon or the given N is out of range.';
			
COMMENT ON FUNCTION ST_IsClosed(geometry ) IS 'args: g - Returns TRUE if the LINESTRINGs start and end points are coincident. For Polyhedral surface is closed (volumetric).';
			
COMMENT ON FUNCTION ST_IsCollection(geometry ) IS 'args: g - Returns TRUE if the argument is a collection (MULTI*, GEOMETRYCOLLECTION, ...)';
			
COMMENT ON FUNCTION ST_IsEmpty(geometry ) IS 'args: geomA - Returns true if this Geometry is an empty geometrycollection, polygon, point etc.';
			
COMMENT ON FUNCTION ST_IsRing(geometry ) IS 'args: g - Returns TRUE if this LINESTRING is both closed and simple.';
			
COMMENT ON FUNCTION ST_IsSimple(geometry ) IS 'args: geomA - Returns (TRUE) if this Geometry has no anomalous geometric points, such as self intersection or self tangency.';
			
COMMENT ON FUNCTION ST_IsValid(geometry ) IS 'args: g - Returns true if the ST_Geometry is well formed.';
			
COMMENT ON FUNCTION ST_IsValid(geometry , integer ) IS 'args: g, flags - Returns true if the ST_Geometry is well formed.';
			
COMMENT ON FUNCTION ST_IsValidReason(geometry ) IS 'args: geomA - Returns text stating if a geometry is valid or not and if not valid, a reason why.';
			
COMMENT ON FUNCTION ST_IsValidReason(geometry , integer ) IS 'args: geomA, flags - Returns text stating if a geometry is valid or not and if not valid, a reason why.';
			
COMMENT ON FUNCTION ST_IsValidDetail(geometry ) IS 'args: geom - Returns a valid_detail (valid,reason,location) row stating if a geometry is valid or not and if not valid, a reason why and a location where.';
			
COMMENT ON FUNCTION ST_IsValidDetail(geometry , integer ) IS 'args: geom, flags - Returns a valid_detail (valid,reason,location) row stating if a geometry is valid or not and if not valid, a reason why and a location where.';
			
COMMENT ON FUNCTION ST_M(geometry ) IS 'args: a_point - Return the M coordinate of the point, or NULL if not available. Input must be a point.';
			
COMMENT ON FUNCTION ST_NDims(geometry ) IS 'args: g1 - Returns coordinate dimension of the geometry as a small int. Values are: 2,3 or 4.';
			
COMMENT ON FUNCTION ST_NPoints(geometry ) IS 'args: g1 - Return the number of points (vertexes) in a geometry.';
			
COMMENT ON FUNCTION ST_NRings(geometry ) IS 'args: geomA - If the geometry is a polygon or multi-polygon returns the number of rings.';
			
COMMENT ON FUNCTION ST_NumGeometries(geometry ) IS 'args: geom - If geometry is a GEOMETRYCOLLECTION (or MULTI*) return the number of geometries, for single geometries will return 1, otherwise return NULL.';
			
COMMENT ON FUNCTION ST_NumInteriorRings(geometry ) IS 'args: a_polygon - Return the number of interior rings of the first polygon in the geometry. This will work with both POLYGON and MULTIPOLYGON types but only looks at the first polygon. Return NULL if there is no polygon in the geometry.';
			
COMMENT ON FUNCTION ST_NumInteriorRing(geometry ) IS 'args: a_polygon - Return the number of interior rings of the first polygon in the geometry. Synonym to ST_NumInteriorRings.';
			
COMMENT ON FUNCTION ST_NumPatches(geometry ) IS 'args: g1 - Return the number of faces on a Polyhedral Surface. Will return null for non-polyhedral geometries.';
			
COMMENT ON FUNCTION ST_NumPoints(geometry ) IS 'args: g1 - Return the number of points in an ST_LineString or ST_CircularString value.';
			
COMMENT ON FUNCTION ST_PatchN(geometry , integer ) IS 'args: geomA, n - Return the 1-based Nth geometry (face) if the geometry is a POLYHEDRALSURFACE, POLYHEDRALSURFACEM. Otherwise, return NULL.';
			
COMMENT ON FUNCTION ST_PointN(geometry , integer ) IS 'args: a_linestring, n - Return the Nth point in the first linestring or circular linestring in the geometry. Return NULL if there is no linestring in the geometry.';
			
COMMENT ON FUNCTION ST_SRID(geometry ) IS 'args: g1 - Returns the spatial reference identifier for the ST_Geometry as defined in spatial_ref_sys table.';
			
COMMENT ON FUNCTION ST_StartPoint(geometry ) IS 'args: geomA - Returns the first point of a LINESTRING geometry as a POINT.';
			
COMMENT ON FUNCTION ST_Summary(geometry ) IS 'args: g - Returns a text summary of the contents of the geometry.';
			
COMMENT ON FUNCTION ST_Summary(geography ) IS 'args: g - Returns a text summary of the contents of the geometry.';
			
COMMENT ON FUNCTION ST_X(geometry ) IS 'args: a_point - Return the X coordinate of the point, or NULL if not available. Input must be a point.';
			
COMMENT ON FUNCTION ST_XMax(box3d ) IS 'args: aGeomorBox2DorBox3D - Returns X maxima of a bounding box 2d or 3d or a geometry.';
			
COMMENT ON FUNCTION ST_XMin(box3d ) IS 'args: aGeomorBox2DorBox3D - Returns X minima of a bounding box 2d or 3d or a geometry.';
			
COMMENT ON FUNCTION ST_Y(geometry ) IS 'args: a_point - Return the Y coordinate of the point, or NULL if not available. Input must be a point.';
			
COMMENT ON FUNCTION ST_YMax(box3d ) IS 'args: aGeomorBox2DorBox3D - Returns Y maxima of a bounding box 2d or 3d or a geometry.';
			
COMMENT ON FUNCTION ST_YMin(box3d ) IS 'args: aGeomorBox2DorBox3D - Returns Y minima of a bounding box 2d or 3d or a geometry.';
			
COMMENT ON FUNCTION ST_Z(geometry ) IS 'args: a_point - Return the Z coordinate of the point, or NULL if not available. Input must be a point.';
			
COMMENT ON FUNCTION ST_ZMax(box3d ) IS 'args: aGeomorBox2DorBox3D - Returns Z minima of a bounding box 2d or 3d or a geometry.';
			
COMMENT ON FUNCTION ST_Zmflag(geometry ) IS 'args: geomA - Returns ZM (dimension semantic) flag of the geometries as a small int. Values are: 0=2d, 1=3dm, 2=3dz, 3=4d.';
			
COMMENT ON FUNCTION ST_ZMin(box3d ) IS 'args: aGeomorBox2DorBox3D - Returns Z minima of a bounding box 2d or 3d or a geometry.';
			
COMMENT ON FUNCTION ST_AddPoint(geometry, geometry) IS 'args: linestring, point - Adds a point to a LineString before point <position> (0-based index).';
			
COMMENT ON FUNCTION ST_AddPoint(geometry, geometry, integer) IS 'args: linestring, point, position - Adds a point to a LineString before point <position> (0-based index).';
			
COMMENT ON FUNCTION ST_Affine(geometry , float , float , float , float , float , float , float , float , float , float , float , float ) IS 'args: geomA, a, b, c, d, e, f, g, h, i, xoff, yoff, zoff - Applies a 3d affine transformation to the geometry to do things like translate, rotate, scale in one step.';
			
COMMENT ON FUNCTION ST_Affine(geometry , float , float , float , float , float , float ) IS 'args: geomA, a, b, d, e, xoff, yoff - Applies a 3d affine transformation to the geometry to do things like translate, rotate, scale in one step.';
			
COMMENT ON FUNCTION ST_Force2D(geometry ) IS 'args: geomA - Forces the geometries into a "2-dimensional mode" so that all output representations will only have the X and Y coordinates.';
			
COMMENT ON FUNCTION ST_Force3D(geometry ) IS 'args: geomA - Forces the geometries into XYZ mode. This is an alias for ST_Force3DZ.';
			
COMMENT ON FUNCTION ST_Force3DZ(geometry ) IS 'args: geomA - Forces the geometries into XYZ mode. This is a synonym for ST_Force3D.';
			
COMMENT ON FUNCTION ST_Force3DM(geometry ) IS 'args: geomA - Forces the geometries into XYM mode.';
			
COMMENT ON FUNCTION ST_Force4D(geometry ) IS 'args: geomA - Forces the geometries into XYZM mode.';
			
COMMENT ON FUNCTION ST_ForceCollection(geometry ) IS 'args: geomA - Converts the geometry into a GEOMETRYCOLLECTION.';
			
COMMENT ON FUNCTION ST_ForceSFS(geometry ) IS 'args: geomA - Forces the geometries to use SFS 1.1 geometry types only.';
			
COMMENT ON FUNCTION ST_ForceSFS(geometry , text ) IS 'args: geomA, version - Forces the geometries to use SFS 1.1 geometry types only.';
			
COMMENT ON FUNCTION ST_ForceRHR(geometry) IS 'args: g - Forces the orientation of the vertices in a polygon to follow the Right-Hand-Rule.';
			
COMMENT ON FUNCTION ST_LineMerge(geometry ) IS 'args: amultilinestring - Returns a (set of) LineString(s) formed by sewing together a MULTILINESTRING.';
			
COMMENT ON FUNCTION ST_CollectionExtract(geometry , integer ) IS 'args: collection, type - Given a (multi)geometry, returns a (multi)geometry consisting only of elements of the specified type.';
			
COMMENT ON FUNCTION ST_CollectionHomogenize(geometry ) IS 'args: collection - Given a geometry collection, returns the "simplest" representation of the contents.';
			
COMMENT ON FUNCTION ST_Multi(geometry ) IS 'args: g1 - Returns the geometry as a MULTI* geometry. If the geometry is already a MULTI*, it is returned unchanged.';
			
COMMENT ON FUNCTION ST_RemovePoint(geometry, integer) IS 'args: linestring, offset - Removes point from a linestring. Offset is 0-based.';
			
COMMENT ON FUNCTION ST_Reverse(geometry ) IS 'args: g1 - Returns the geometry with vertex order reversed.';
			
COMMENT ON FUNCTION ST_Rotate(geometry, float) IS 'args: geomA, rotRadians - Rotate a geometry rotRadians counter-clockwise about an origin.';
			
COMMENT ON FUNCTION ST_Rotate(geometry, float, float, float) IS 'args: geomA, rotRadians, x0, y0 - Rotate a geometry rotRadians counter-clockwise about an origin.';
			
COMMENT ON FUNCTION ST_Rotate(geometry, float, geometry) IS 'args: geomA, rotRadians, pointOrigin - Rotate a geometry rotRadians counter-clockwise about an origin.';
			
COMMENT ON FUNCTION ST_RotateX(geometry, float) IS 'args: geomA, rotRadians - Rotate a geometry rotRadians about the X axis.';
			
COMMENT ON FUNCTION ST_RotateY(geometry, float) IS 'args: geomA, rotRadians - Rotate a geometry rotRadians about the Y axis.';
			
COMMENT ON FUNCTION ST_RotateZ(geometry, float) IS 'args: geomA, rotRadians - Rotate a geometry rotRadians about the Z axis.';
			
COMMENT ON FUNCTION ST_Scale(geometry , float, float, float) IS 'args: geomA, XFactor, YFactor, ZFactor - Scales the geometry to a new size by multiplying the ordinates with the parameters. Ie: ST_Scale(geom, Xfactor, Yfactor, Zfactor).';
			
COMMENT ON FUNCTION ST_Scale(geometry , float, float) IS 'args: geomA, XFactor, YFactor - Scales the geometry to a new size by multiplying the ordinates with the parameters. Ie: ST_Scale(geom, Xfactor, Yfactor, Zfactor).';
			
COMMENT ON FUNCTION ST_Segmentize(geometry , float ) IS 'args: geom, max_segment_length - Return a modified geometry/geography having no segment longer than the given distance. Distance computation is performed in 2d only. For geometry, length units are in units of spatial reference. For geography, units are in meters.';
			
COMMENT ON FUNCTION ST_Segmentize(geography , float ) IS 'args: geog, max_segment_length - Return a modified geometry/geography having no segment longer than the given distance. Distance computation is performed in 2d only. For geometry, length units are in units of spatial reference. For geography, units are in meters.';
			
COMMENT ON FUNCTION ST_SetPoint(geometry, integer, geometry) IS 'args: linestring, zerobasedposition, point - Replace point N of linestring with given point. Index is 0-based.';
			
COMMENT ON FUNCTION ST_SetSRID(geometry , integer ) IS 'args: geom, srid - Sets the SRID on a geometry to a particular integer value.';
			
COMMENT ON FUNCTION ST_SnapToGrid(geometry , float , float , float , float ) IS 'args: geomA, originX, originY, sizeX, sizeY - Snap all points of the input geometry to a regular grid.';
			
COMMENT ON FUNCTION ST_SnapToGrid(geometry , float , float ) IS 'args: geomA, sizeX, sizeY - Snap all points of the input geometry to a regular grid.';
			
COMMENT ON FUNCTION ST_SnapToGrid(geometry , float ) IS 'args: geomA, size - Snap all points of the input geometry to a regular grid.';
			
COMMENT ON FUNCTION ST_SnapToGrid(geometry , geometry , float , float , float , float ) IS 'args: geomA, pointOrigin, sizeX, sizeY, sizeZ, sizeM - Snap all points of the input geometry to a regular grid.';
			
COMMENT ON FUNCTION ST_Snap(geometry , geometry , float ) IS 'args: input, reference, tolerance - Snap segments and vertices of input geometry to vertices of a reference geometry.';
			
COMMENT ON FUNCTION ST_Transform(geometry , integer ) IS 'args: g1, srid - Returns a new geometry with its coordinates transformed to the SRID referenced by the integer parameter.';
			
COMMENT ON FUNCTION ST_Translate(geometry , float , float ) IS 'args: g1, deltax, deltay - Translates the geometry to a new location using the numeric parameters as offsets. Ie: ST_Translate(geom, X, Y) or ST_Translate(geom, X, Y,Z).';
			
COMMENT ON FUNCTION ST_Translate(geometry , float , float , float ) IS 'args: g1, deltax, deltay, deltaz - Translates the geometry to a new location using the numeric parameters as offsets. Ie: ST_Translate(geom, X, Y) or ST_Translate(geom, X, Y,Z).';
			
COMMENT ON FUNCTION ST_TransScale(geometry , float, float, float, float) IS 'args: geomA, deltaX, deltaY, XFactor, YFactor - Translates the geometry using the deltaX and deltaY args, then scales it using the XFactor, YFactor args, working in 2D only.';
			
COMMENT ON FUNCTION ST_AsBinary(geometry ) IS 'args: g1 - Return the Well-Known Binary (WKB) representation of the geometry/geography without SRID meta data.';
			
COMMENT ON FUNCTION ST_AsBinary(geometry , text ) IS 'args: g1, NDR_or_XDR - Return the Well-Known Binary (WKB) representation of the geometry/geography without SRID meta data.';
			
COMMENT ON FUNCTION ST_AsBinary(geography ) IS 'args: g1 - Return the Well-Known Binary (WKB) representation of the geometry/geography without SRID meta data.';
			
COMMENT ON FUNCTION ST_AsBinary(geography , text ) IS 'args: g1, NDR_or_XDR - Return the Well-Known Binary (WKB) representation of the geometry/geography without SRID meta data.';
			
COMMENT ON FUNCTION ST_AsEWKB(geometry ) IS 'args: g1 - Return the Well-Known Binary (WKB) representation of the geometry with SRID meta data.';
			
COMMENT ON FUNCTION ST_AsEWKB(geometry , text ) IS 'args: g1, NDR_or_XDR - Return the Well-Known Binary (WKB) representation of the geometry with SRID meta data.';
			
COMMENT ON FUNCTION ST_AsEWKT(geometry ) IS 'args: g1 - Return the Well-Known Text (WKT) representation of the geometry with SRID meta data.';
			
COMMENT ON FUNCTION ST_AsEWKT(geography ) IS 'args: g1 - Return the Well-Known Text (WKT) representation of the geometry with SRID meta data.';
			
COMMENT ON FUNCTION ST_AsGeoJSON(geometry , integer , integer ) IS 'args: geom, maxdecimaldigits=15, options=0 - Return the geometry as a GeoJSON element.';
			
COMMENT ON FUNCTION ST_AsGeoJSON(geography , integer , integer ) IS 'args: geog, maxdecimaldigits=15, options=0 - Return the geometry as a GeoJSON element.';
			
COMMENT ON FUNCTION ST_AsGeoJSON(integer , geometry , integer , integer ) IS 'args: gj_version, geom, maxdecimaldigits=15, options=0 - Return the geometry as a GeoJSON element.';
			
COMMENT ON FUNCTION ST_AsGeoJSON(integer , geography , integer , integer ) IS 'args: gj_version, geog, maxdecimaldigits=15, options=0 - Return the geometry as a GeoJSON element.';
			
COMMENT ON FUNCTION ST_AsGML(integer , geometry , integer , integer , text , text ) IS 'args: version, geom, maxdecimaldigits=15, options=0, nprefix=null, id=null - Return the geometry as a GML version 2 or 3 element.';
			
COMMENT ON FUNCTION ST_AsGML(integer , geography , integer , integer , text , text ) IS 'args: version, geog, maxdecimaldigits=15, options=0, nprefix=null, id=null - Return the geometry as a GML version 2 or 3 element.';
			
COMMENT ON FUNCTION ST_AsHEXEWKB(geometry , text ) IS 'args: g1, NDRorXDR - Returns a Geometry in HEXEWKB format (as text) using either little-endian (NDR) or big-endian (XDR) encoding.';
			
COMMENT ON FUNCTION ST_AsHEXEWKB(geometry ) IS 'args: g1 - Returns a Geometry in HEXEWKB format (as text) using either little-endian (NDR) or big-endian (XDR) encoding.';
			
COMMENT ON FUNCTION ST_AsKML(geometry , integer ) IS 'args: geom, maxdecimaldigits=15 - Return the geometry as a KML element. Several variants. Default version=2, default precision=15';
			
COMMENT ON FUNCTION ST_AsKML(geography , integer ) IS 'args: geog, maxdecimaldigits=15 - Return the geometry as a KML element. Several variants. Default version=2, default precision=15';
			
COMMENT ON FUNCTION ST_AsKML(integer , geometry , integer , text ) IS 'args: version, geom, maxdecimaldigits=15, nprefix=NULL - Return the geometry as a KML element. Several variants. Default version=2, default precision=15';
			
COMMENT ON FUNCTION ST_AsKML(integer , geography , integer , text ) IS 'args: version, geog, maxdecimaldigits=15, nprefix=NULL - Return the geometry as a KML element. Several variants. Default version=2, default precision=15';
			
COMMENT ON FUNCTION ST_AsSVG(geometry , integer , integer ) IS 'args: geom, rel=0, maxdecimaldigits=15 - Returns a Geometry in SVG path data given a geometry or geography object.';
			
COMMENT ON FUNCTION ST_AsSVG(geography , integer , integer ) IS 'args: geog, rel=0, maxdecimaldigits=15 - Returns a Geometry in SVG path data given a geometry or geography object.';
			
COMMENT ON FUNCTION ST_AsX3D(geometry , integer , integer ) IS 'args: g1, maxdecimaldigits=15, options=0 - Returns a Geometry in X3D xml node element format: ISO-IEC-19776-1.2-X3DEncodings-XML';
			
COMMENT ON FUNCTION ST_GeoHash(geometry , integer ) IS 'args: geom, maxchars=full_precision_of_point - Return a GeoHash representation of the geometry.';
			
COMMENT ON FUNCTION ST_AsText(geometry ) IS 'args: g1 - Return the Well-Known Text (WKT) representation of the geometry/geography without SRID metadata.';
			
COMMENT ON FUNCTION ST_AsText(geography ) IS 'args: g1 - Return the Well-Known Text (WKT) representation of the geometry/geography without SRID metadata.';
			
COMMENT ON FUNCTION ST_AsLatLonText(geometry ) IS 'args: pt - Return the Degrees, Minutes, Seconds representation of the given point.';
			
COMMENT ON FUNCTION ST_AsLatLonText(geometry , text ) IS 'args: pt, format - Return the Degrees, Minutes, Seconds representation of the given point.';
			
COMMENT ON FUNCTION ST_3DClosestPoint(geometry , geometry ) IS 'args: g1, g2 - Returns the 3-dimensional point on g1 that is closest to g2. This is the first point of the 3D shortest line.';
			
COMMENT ON FUNCTION ST_3DDistance(geometry , geometry ) IS 'args: g1, g2 - For geometry type Returns the 3-dimensional cartesian minimum distance (based on spatial ref) between two geometries in projected units.';
			
COMMENT ON FUNCTION ST_3DDWithin(geometry , geometry , double precision ) IS 'args: g1, g2, distance_of_srid - For 3d (z) geometry type Returns true if two geometries 3d distance is within number of units.';
			
COMMENT ON FUNCTION ST_3DDFullyWithin(geometry , geometry , double precision ) IS 'args: g1, g2, distance - Returns true if all of the 3D geometries are within the specified distance of one another.';
			
COMMENT ON FUNCTION ST_3DIntersects(geometry, geometry) IS 'args: geomA, geomB - Returns TRUE if the Geometries "spatially intersect" in 3d - only for points and linestrings';
			
COMMENT ON FUNCTION ST_3DLongestLine(geometry , geometry ) IS 'args: g1, g2 - Returns the 3-dimensional longest line between two geometries';
			
COMMENT ON FUNCTION ST_3DMaxDistance(geometry , geometry ) IS 'args: g1, g2 - For geometry type Returns the 3-dimensional cartesian maximum distance (based on spatial ref) between two geometries in projected units.';
			
COMMENT ON FUNCTION ST_3DShortestLine(geometry , geometry ) IS 'args: g1, g2 - Returns the 3-dimensional shortest line between two geometries';
			
COMMENT ON FUNCTION ST_Area(geometry ) IS 'args: g1 - Returns the area of the surface if it is a polygon or multi-polygon. For "geometry" type area is in SRID units. For "geography" area is in square meters.';
			
COMMENT ON FUNCTION ST_Area(geography , boolean ) IS 'args: geog, use_spheroid=true - Returns the area of the surface if it is a polygon or multi-polygon. For "geometry" type area is in SRID units. For "geography" area is in square meters.';
			
COMMENT ON FUNCTION ST_Azimuth(geometry , geometry ) IS 'args: pointA, pointB - Returns the north-based azimuth as the angle in radians measured clockwise from the vertical on pointA to pointB.';
			
COMMENT ON FUNCTION ST_Azimuth(geography , geography ) IS 'args: pointA, pointB - Returns the north-based azimuth as the angle in radians measured clockwise from the vertical on pointA to pointB.';
			
COMMENT ON FUNCTION ST_Centroid(geometry ) IS 'args: g1 - Returns the geometric center of a geometry.';
			
COMMENT ON FUNCTION ST_ClosestPoint(geometry , geometry ) IS 'args: g1, g2 - Returns the 2-dimensional point on g1 that is closest to g2. This is the first point of the shortest line.';
			
COMMENT ON FUNCTION ST_Contains(geometry , geometry ) IS 'args: geomA, geomB - Returns true if and only if no points of B lie in the exterior of A, and at least one point of the interior of B lies in the interior of A.';
			
COMMENT ON FUNCTION ST_ContainsProperly(geometry , geometry ) IS 'args: geomA, geomB - Returns true if B intersects the interior of A but not the boundary (or exterior). A does not contain properly itself, but does contain itself.';
			
COMMENT ON FUNCTION ST_Covers(geometry , geometry ) IS 'args: geomA, geomB - Returns 1 (TRUE) if no point in Geometry B is outside Geometry A';
			
COMMENT ON FUNCTION ST_Covers(geography , geography ) IS 'args: geogpolyA, geogpointB - Returns 1 (TRUE) if no point in Geometry B is outside Geometry A';
			
COMMENT ON FUNCTION ST_CoveredBy(geometry , geometry ) IS 'args: geomA, geomB - Returns 1 (TRUE) if no point in Geometry/Geography A is outside Geometry/Geography B';
			
COMMENT ON FUNCTION ST_CoveredBy(geography , geography ) IS 'args: geogA, geogB - Returns 1 (TRUE) if no point in Geometry/Geography A is outside Geometry/Geography B';
			
COMMENT ON FUNCTION ST_Crosses(geometry , geometry ) IS 'args: g1, g2 - Returns TRUE if the supplied geometries have some, but not all, interior points in common.';
			
COMMENT ON FUNCTION ST_LineCrossingDirection(geometry , geometry ) IS 'args: linestringA, linestringB - Given 2 linestrings, returns a number between -3 and 3 denoting what kind of crossing behavior. 0 is no crossing.';
			
COMMENT ON FUNCTION ST_Disjoint(geometry, geometry) IS 'args: A, B - Returns TRUE if the Geometries do not "spatially intersect" - if they do not share any space together.';
			
COMMENT ON FUNCTION ST_Distance(geometry , geometry ) IS 'args: g1, g2 - For geometry type Returns the 2-dimensional cartesian minimum distance (based on spatial ref) between two geometries in projected units. For geography type defaults to return spheroidal minimum distance between two geographies in meters.';
			
COMMENT ON FUNCTION ST_Distance(geography , geography ) IS 'args: gg1, gg2 - For geometry type Returns the 2-dimensional cartesian minimum distance (based on spatial ref) between two geometries in projected units. For geography type defaults to return spheroidal minimum distance between two geographies in meters.';
			
COMMENT ON FUNCTION ST_Distance(geography , geography , boolean ) IS 'args: gg1, gg2, use_spheroid - For geometry type Returns the 2-dimensional cartesian minimum distance (based on spatial ref) between two geometries in projected units. For geography type defaults to return spheroidal minimum distance between two geographies in meters.';
			
COMMENT ON FUNCTION ST_HausdorffDistance(geometry , geometry ) IS 'args: g1, g2 - Returns the Hausdorff distance between two geometries. Basically a measure of how similar or dissimilar 2 geometries are. Units are in the units of the spatial reference system of the geometries.';
			
COMMENT ON FUNCTION ST_HausdorffDistance(geometry , geometry , float) IS 'args: g1, g2, densifyFrac - Returns the Hausdorff distance between two geometries. Basically a measure of how similar or dissimilar 2 geometries are. Units are in the units of the spatial reference system of the geometries.';
			
COMMENT ON FUNCTION ST_MaxDistance(geometry , geometry ) IS 'args: g1, g2 - Returns the 2-dimensional largest distance between two geometries in projected units.';
			
COMMENT ON FUNCTION ST_Distance_Sphere(geometry , geometry ) IS 'args: geomlonlatA, geomlonlatB - Returns minimum distance in meters between two lon/lat geometries. Uses a spherical earth and radius of 6370986 meters. Faster than ST_Distance_Spheroid , but less accurate. PostGIS versions prior to 1.5 only implemented for points.';
			
COMMENT ON FUNCTION ST_Distance_Spheroid(geometry , geometry , spheroid ) IS 'args: geomlonlatA, geomlonlatB, measurement_spheroid - Returns the minimum distance between two lon/lat geometries given a particular spheroid. PostGIS versions prior to 1.5 only support points.';
			
COMMENT ON FUNCTION ST_DFullyWithin(geometry , geometry , double precision ) IS 'args: g1, g2, distance - Returns true if all of the geometries are within the specified distance of one another';
			
COMMENT ON FUNCTION ST_DWithin(geometry , geometry , double precision ) IS 'args: g1, g2, distance_of_srid - Returns true if the geometries are within the specified distance of one another. For geometry units are in those of spatial reference and For geography units are in meters and measurement is defaulted to use_spheroid=true (measure around spheroid), for faster check, use_spheroid=false to measure along sphere.';
			
COMMENT ON FUNCTION ST_DWithin(geography , geography , double precision ) IS 'args: gg1, gg2, distance_meters - Returns true if the geometries are within the specified distance of one another. For geometry units are in those of spatial reference and For geography units are in meters and measurement is defaulted to use_spheroid=true (measure around spheroid), for faster check, use_spheroid=false to measure along sphere.';
			
COMMENT ON FUNCTION ST_DWithin(geography , geography , double precision , boolean ) IS 'args: gg1, gg2, distance_meters, use_spheroid - Returns true if the geometries are within the specified distance of one another. For geometry units are in those of spatial reference and For geography units are in meters and measurement is defaulted to use_spheroid=true (measure around spheroid), for faster check, use_spheroid=false to measure along sphere.';
			
COMMENT ON FUNCTION ST_Equals(geometry , geometry ) IS 'args: A, B - Returns true if the given geometries represent the same geometry. Directionality is ignored.';
			
COMMENT ON FUNCTION ST_HasArc(geometry ) IS 'args: geomA - Returns true if a geometry or geometry collection contains a circular string';
			
COMMENT ON FUNCTION ST_Intersects(geometry, geometry) IS 'args: geomA, geomB - Returns TRUE if the Geometries/Geography "spatially intersect in 2D" - (share any portion of space) and FALSE if they dont (they are Disjoint). For geography -- tolerance is 0.00001 meters (so any points that close are considered to intersect)';
			
COMMENT ON FUNCTION ST_Intersects(geography, geography) IS 'args: geogA, geogB - Returns TRUE if the Geometries/Geography "spatially intersect in 2D" - (share any portion of space) and FALSE if they dont (they are Disjoint). For geography -- tolerance is 0.00001 meters (so any points that close are considered to intersect)';
			
COMMENT ON FUNCTION ST_Length(geometry ) IS 'args: a_2dlinestring - Returns the 2d length of the geometry if it is a linestring or multilinestring. geometry are in units of spatial reference and geography are in meters (default spheroid)';
			
COMMENT ON FUNCTION ST_Length(geography , boolean ) IS 'args: geog, use_spheroid=true - Returns the 2d length of the geometry if it is a linestring or multilinestring. geometry are in units of spatial reference and geography are in meters (default spheroid)';
			
COMMENT ON FUNCTION ST_Length2D(geometry ) IS 'args: a_2dlinestring - Returns the 2-dimensional length of the geometry if it is a linestring or multi-linestring. This is an alias for ST_Length';
			
COMMENT ON FUNCTION ST_3DLength(geometry ) IS 'args: a_3dlinestring - Returns the 3-dimensional or 2-dimensional length of the geometry if it is a linestring or multi-linestring.';
			
COMMENT ON FUNCTION ST_Length_Spheroid(geometry , spheroid ) IS 'args: a_linestring, a_spheroid - Calculates the 2D or 3D length of a linestring/multilinestring on an ellipsoid. This is useful if the coordinates of the geometry are in longitude/latitude and a length is desired without reprojection.';
			
COMMENT ON FUNCTION ST_Length2D_Spheroid(geometry , spheroid ) IS 'args: a_linestring, a_spheroid - Calculates the 2D length of a linestring/multilinestring on an ellipsoid. This is useful if the coordinates of the geometry are in longitude/latitude and a length is desired without reprojection.';
			
COMMENT ON FUNCTION ST_3DLength_Spheroid(geometry , spheroid ) IS 'args: a_linestring, a_spheroid - Calculates the length of a geometry on an ellipsoid, taking the elevation into account. This is just an alias for ST_Length_Spheroid.';
			
COMMENT ON FUNCTION ST_LongestLine(geometry , geometry ) IS 'args: g1, g2 - Returns the 2-dimensional longest line points of two geometries. The function will only return the first longest line if more than one, that the function finds. The line returned will always start in g1 and end in g2. The length of the line this function returns will always be the same as st_maxdistance returns for g1 and g2.';
			
COMMENT ON FUNCTION ST_OrderingEquals(geometry , geometry ) IS 'args: A, B - Returns true if the given geometries represent the same geometry and points are in the same directional order.';
			
COMMENT ON FUNCTION ST_Overlaps(geometry , geometry ) IS 'args: A, B - Returns TRUE if the Geometries share space, are of the same dimension, but are not completely contained by each other.';
			
COMMENT ON FUNCTION ST_Perimeter(geometry ) IS 'args: g1 - Return the length measurement of the boundary of an ST_Surface or ST_MultiSurface geometry or geography. (Polygon, Multipolygon). geometry measurement is in units of spatial reference and geography is in meters.';
			
COMMENT ON FUNCTION ST_Perimeter(geography , boolean ) IS 'args: geog, use_spheroid=true - Return the length measurement of the boundary of an ST_Surface or ST_MultiSurface geometry or geography. (Polygon, Multipolygon). geometry measurement is in units of spatial reference and geography is in meters.';
			
COMMENT ON FUNCTION ST_Perimeter2D(geometry ) IS 'args: geomA - Returns the 2-dimensional perimeter of the geometry, if it is a polygon or multi-polygon. This is currently an alias for ST_Perimeter.';
			
COMMENT ON FUNCTION ST_3DPerimeter(geometry ) IS 'args: geomA - Returns the 3-dimensional perimeter of the geometry, if it is a polygon or multi-polygon.';
			
COMMENT ON FUNCTION ST_PointOnSurface(geometry ) IS 'args: g1 - Returns a POINT guaranteed to lie on the surface.';
			
COMMENT ON FUNCTION ST_Project(geography , float , float ) IS 'args: g1, distance, azimuth - Returns a POINT projected from a start point using a distance in meters and bearing (azimuth) in radians.';
			
COMMENT ON FUNCTION ST_Relate(geometry , geometry , text ) IS 'args: geomA, geomB, intersectionMatrixPattern - Returns true if this Geometry is spatially related to anotherGeometry, by testing for intersections between the Interior, Boundary and Exterior of the two geometries as specified by the values in the intersectionMatrixPattern. If no intersectionMatrixPattern is passed in, then returns the maximum intersectionMatrixPattern that relates the 2 geometries.';
			
COMMENT ON FUNCTION ST_Relate(geometry , geometry ) IS 'args: geomA, geomB - Returns true if this Geometry is spatially related to anotherGeometry, by testing for intersections between the Interior, Boundary and Exterior of the two geometries as specified by the values in the intersectionMatrixPattern. If no intersectionMatrixPattern is passed in, then returns the maximum intersectionMatrixPattern that relates the 2 geometries.';
			
COMMENT ON FUNCTION ST_Relate(geometry , geometry , int ) IS 'args: geomA, geomB, BoundaryNodeRule - Returns true if this Geometry is spatially related to anotherGeometry, by testing for intersections between the Interior, Boundary and Exterior of the two geometries as specified by the values in the intersectionMatrixPattern. If no intersectionMatrixPattern is passed in, then returns the maximum intersectionMatrixPattern that relates the 2 geometries.';
			
COMMENT ON FUNCTION ST_RelateMatch(text , text ) IS 'args: intersectionMatrix, intersectionMatrixPattern - Returns true if intersectionMattrixPattern1 implies intersectionMatrixPattern2';
			
COMMENT ON FUNCTION ST_ShortestLine(geometry , geometry ) IS 'args: g1, g2 - Returns the 2-dimensional shortest line between two geometries';
			
COMMENT ON FUNCTION ST_Touches(geometry , geometry ) IS 'args: g1, g2 - Returns TRUE if the geometries have at least one point in common, but their interiors do not intersect.';
			
COMMENT ON FUNCTION ST_Within(geometry , geometry ) IS 'args: A, B - Returns true if the geometry A is completely inside geometry B';
			
COMMENT ON FUNCTION ST_Buffer(geometry , float ) IS 'args: g1, radius_of_buffer - (T) For geometry: Returns a geometry that represents all points whose distance from this Geometry is less than or equal to distance. Calculations are in the Spatial Reference System of this Geometry. For geography: Uses a planar transform wrapper. Introduced in 1.5 support for different end cap and mitre settings to control shape. buffer_style options: quad_segs=#,endcap=round|flat|square,join=round|mitre|bevel,mitre_limit=#.#';
			
COMMENT ON FUNCTION ST_Buffer(geometry , float , integer ) IS 'args: g1, radius_of_buffer, num_seg_quarter_circle - (T) For geometry: Returns a geometry that represents all points whose distance from this Geometry is less than or equal to distance. Calculations are in the Spatial Reference System of this Geometry. For geography: Uses a planar transform wrapper. Introduced in 1.5 support for different end cap and mitre settings to control shape. buffer_style options: quad_segs=#,endcap=round|flat|square,join=round|mitre|bevel,mitre_limit=#.#';
			
COMMENT ON FUNCTION ST_Buffer(geometry , float , text ) IS 'args: g1, radius_of_buffer, buffer_style_parameters - (T) For geometry: Returns a geometry that represents all points whose distance from this Geometry is less than or equal to distance. Calculations are in the Spatial Reference System of this Geometry. For geography: Uses a planar transform wrapper. Introduced in 1.5 support for different end cap and mitre settings to control shape. buffer_style options: quad_segs=#,endcap=round|flat|square,join=round|mitre|bevel,mitre_limit=#.#';
			
COMMENT ON FUNCTION ST_Buffer(geography , float ) IS 'args: g1, radius_of_buffer_in_meters - (T) For geometry: Returns a geometry that represents all points whose distance from this Geometry is less than or equal to distance. Calculations are in the Spatial Reference System of this Geometry. For geography: Uses a planar transform wrapper. Introduced in 1.5 support for different end cap and mitre settings to control shape. buffer_style options: quad_segs=#,endcap=round|flat|square,join=round|mitre|bevel,mitre_limit=#.#';
			
COMMENT ON FUNCTION ST_BuildArea(geometry ) IS 'args: A - Creates an areal geometry formed by the constituent linework of given geometry';
			
COMMENT ON AGGREGATE ST_Collect(geometry) IS 'args: g1field - Return a specified ST_Geometry value from a collection of other geometries.';
			
COMMENT ON FUNCTION ST_Collect(geometry, geometry) IS 'args: g1, g2 - Return a specified ST_Geometry value from a collection of other geometries.';
			
COMMENT ON FUNCTION ST_Collect(geometry[]) IS 'args: g1_array - Return a specified ST_Geometry value from a collection of other geometries.';
			
COMMENT ON FUNCTION ST_ConcaveHull(geometry , float , boolean ) IS 'args: geomA, target_percent, allow_holes=false - The concave hull of a geometry represents a possibly concave geometry that encloses all geometries within the set. You can think of it as shrink wrapping.';
			
COMMENT ON FUNCTION ST_ConvexHull(geometry ) IS 'args: geomA - The convex hull of a geometry represents the minimum convex geometry that encloses all geometries within the set.';
			
COMMENT ON FUNCTION ST_CurveToLine(geometry) IS 'args: curveGeom - Converts a CIRCULARSTRING/CURVEDPOLYGON to a LINESTRING/POLYGON';
			
COMMENT ON FUNCTION ST_CurveToLine(geometry, integer) IS 'args: curveGeom, segments_per_qtr_circle - Converts a CIRCULARSTRING/CURVEDPOLYGON to a LINESTRING/POLYGON';
			
COMMENT ON FUNCTION ST_DelaunayTriangles(geometry , float , int4 ) IS 'args: g1, tolerance, flags - Return a Delaunay triangulation around the given input points.';
			
COMMENT ON FUNCTION ST_Difference(geometry , geometry ) IS 'args: geomA, geomB - Returns a geometry that represents that part of geometry A that does not intersect with geometry B.';
			
COMMENT ON FUNCTION ST_Dump(geometry ) IS 'args: g1 - Returns a set of geometry_dump (geom,path) rows, that make up a geometry g1.';
			
COMMENT ON FUNCTION ST_DumpPoints(geometry ) IS 'args: geom - Returns a set of geometry_dump (geom,path) rows of all points that make up a geometry.';
			
COMMENT ON FUNCTION ST_DumpRings(geometry ) IS 'args: a_polygon - Returns a set of geometry_dump rows, representing the exterior and interior rings of a polygon.';
			
COMMENT ON FUNCTION ST_FlipCoordinates(geometry) IS 'args: geom - Returns a version of the given geometry with X and Y axis flipped. Useful for people who have built latitude/longitude features and need to fix them.';
			
COMMENT ON FUNCTION ST_Intersection(geometry, geometry) IS 'args: geomA, geomB - (T) Returns a geometry that represents the shared portion of geomA and geomB. The geography implementation does a transform to geometry to do the intersection and then transform back to WGS84.';
			
COMMENT ON FUNCTION ST_Intersection(geography, geography) IS 'args: geogA, geogB - (T) Returns a geometry that represents the shared portion of geomA and geomB. The geography implementation does a transform to geometry to do the intersection and then transform back to WGS84.';
			
COMMENT ON FUNCTION ST_LineToCurve(geometry ) IS 'args: geomANoncircular - Converts a LINESTRING/POLYGON to a CIRCULARSTRING, CURVED POLYGON';
			
COMMENT ON FUNCTION ST_MakeValid(geometry) IS 'args: input - Attempts to make an invalid geometry valid without losing vertices.';
			
COMMENT ON AGGREGATE ST_MemUnion(geometry) IS 'args: geomfield - Same as ST_Union, only memory-friendly (uses less memory and more processor time).';
			
COMMENT ON FUNCTION ST_MinimumBoundingCircle(geometry , integer ) IS 'args: geomA, num_segs_per_qt_circ=48 - Returns the smallest circle polygon that can fully contain a geometry. Default uses 48 segments per quarter circle.';
			
COMMENT ON AGGREGATE ST_Polygonize(geometry) IS 'args: geomfield - Aggregate. Creates a GeometryCollection containing possible polygons formed from the constituent linework of a set of geometries.';
			
COMMENT ON FUNCTION ST_Polygonize(geometry[]) IS 'args: geom_array - Aggregate. Creates a GeometryCollection containing possible polygons formed from the constituent linework of a set of geometries.';
			
COMMENT ON FUNCTION ST_Node(geometry ) IS 'args: geom - Node a set of linestrings.';
			
COMMENT ON FUNCTION ST_OffsetCurve(geometry , float , text ) IS 'args: line, signed_distance, style_parameters='' - Return an offset line at a given distance and side from an input line. Useful for computing parallel lines about a center line';
			
COMMENT ON FUNCTION ST_RemoveRepeatedPoints(geometry) IS 'args: geom - Returns a version of the given geometry with duplicated points removed.';
			
COMMENT ON FUNCTION ST_SharedPaths(geometry, geometry) IS 'args: lineal1, lineal2 - Returns a collection containing paths shared by the two input linestrings/multilinestrings.';
			
COMMENT ON FUNCTION ST_Shift_Longitude(geometry ) IS 'args: geomA - Reads every point/vertex in every component of every feature in a geometry, and if the longitude coordinate is <0, adds 360 to it. The result would be a 0-360 version of the data to be plotted in a 180 centric map';
			
COMMENT ON FUNCTION ST_Simplify(geometry, float) IS 'args: geomA, tolerance - Returns a "simplified" version of the given geometry using the Douglas-Peucker algorithm.';
			
COMMENT ON FUNCTION ST_SimplifyPreserveTopology(geometry, float) IS 'args: geomA, tolerance - Returns a "simplified" version of the given geometry using the Douglas-Peucker algorithm. Will avoid creating derived geometries (polygons in particular) that are invalid.';
			
COMMENT ON FUNCTION ST_Split(geometry, geometry) IS 'args: input, blade - Returns a collection of geometries resulting by splitting a geometry.';
			
COMMENT ON FUNCTION ST_SymDifference(geometry , geometry ) IS 'args: geomA, geomB - Returns a geometry that represents the portions of A and B that do not intersect. It is called a symmetric difference because ST_SymDifference(A,B) = ST_SymDifference(B,A).';
			
COMMENT ON AGGREGATE ST_Union(geometry) IS 'args: g1field - Returns a geometry that represents the point set union of the Geometries.';
			
COMMENT ON FUNCTION ST_Union(geometry, geometry) IS 'args: g1, g2 - Returns a geometry that represents the point set union of the Geometries.';
			
COMMENT ON FUNCTION ST_Union(geometry[]) IS 'args: g1_array - Returns a geometry that represents the point set union of the Geometries.';
			
COMMENT ON FUNCTION ST_UnaryUnion(geometry ) IS 'args: geom - Like ST_Union, but working at the geometry component level.';
			
COMMENT ON FUNCTION ST_LineInterpolatePoint(geometry , float ) IS 'args: a_linestring, a_fraction - Returns a point interpolated along a line. Second argument is a float8 between 0 and 1 representing fraction of total length of linestring the point has to be located.';
			
COMMENT ON FUNCTION ST_LineLocatePoint(geometry , geometry ) IS 'args: a_linestring, a_point - Returns a float between 0 and 1 representing the location of the closest point on LineString to the given Point, as a fraction of total 2d line length.';
			
COMMENT ON FUNCTION ST_LineSubstring(geometry , float , float ) IS 'args: a_linestring, startfraction, endfraction - Return a linestring being a substring of the input one starting and ending at the given fractions of total 2d length. Second and third arguments are float8 values between 0 and 1.';
			
COMMENT ON FUNCTION ST_LocateAlong(geometry , float , float ) IS 'args: ageom_with_measure, a_measure, offset - Return a derived geometry collection value with elements that match the specified measure. Polygonal elements are not supported.';
			
COMMENT ON FUNCTION ST_LocateBetween(geometry , float , float , float ) IS 'args: geomA, measure_start, measure_end, offset - Return a derived geometry collection value with elements that match the specified range of measures inclusively. Polygonal elements are not supported.';
			
COMMENT ON FUNCTION ST_LocateBetweenElevations(geometry , float , float ) IS 'args: geom_mline, elevation_start, elevation_end - Return a derived geometry (collection) value with elements that intersect the specified range of elevations inclusively. Only 3D, 4D LINESTRINGS and MULTILINESTRINGS are supported.';
			
COMMENT ON FUNCTION ST_InterpolatePoint(geometry , geometry ) IS 'args: line, point - Return the value of the measure dimension of a geometry at the point closed to the provided point.';
			
COMMENT ON FUNCTION ST_AddMeasure(geometry , float , float ) IS 'args: geom_mline, measure_start, measure_end - Return a derived geometry with measure elements linearly interpolated between the start and end points. If the geometry has no measure dimension, one is added. If the geometry has a measure dimension, it is over-written with new values. Only LINESTRINGS and MULTILINESTRINGS are supported.';
			
COMMENT ON FUNCTION AddAuth(text ) IS 'args: auth_token - Add an authorization token to be used in current transaction.';
			
COMMENT ON FUNCTION CheckAuth(text , text , text ) IS 'args: a_schema_name, a_table_name, a_key_column_name - Creates trigger on a table to prevent/allow updates and deletes of rows based on authorization token.';
			
COMMENT ON FUNCTION CheckAuth(text , text ) IS 'args: a_table_name, a_key_column_name - Creates trigger on a table to prevent/allow updates and deletes of rows based on authorization token.';
			
COMMENT ON FUNCTION DisableLongTransactions() IS 'Disable long transaction support. This function removes the long transaction support metadata tables, and drops all triggers attached to lock-checked tables.';
			
COMMENT ON FUNCTION EnableLongTransactions() IS 'Enable long transaction support. This function creates the required metadata tables, needs to be called once before using the other functions in this section. Calling it twice is harmless.';
			
COMMENT ON FUNCTION LockRow(text , text , text , text, timestamp) IS 'args: a_schema_name, a_table_name, a_row_key, an_auth_token, expire_dt - Set lock/authorization for specific row in table';
			
COMMENT ON FUNCTION LockRow(text , text , text, timestamp) IS 'args: a_table_name, a_row_key, an_auth_token, expire_dt - Set lock/authorization for specific row in table';
			
COMMENT ON FUNCTION LockRow(text , text , text) IS 'args: a_table_name, a_row_key, an_auth_token - Set lock/authorization for specific row in table';
			
COMMENT ON FUNCTION UnlockRows(text ) IS 'args: auth_token - Remove all locks held by specified authorization id. Returns the number of locks released.';
			
COMMENT ON AGGREGATE ST_Accum(geometry) IS 'args: geomfield - Aggregate. Constructs an array of geometries.';
			
COMMENT ON FUNCTION Box2D(geometry ) IS 'args: geomA - Returns a BOX2D representing the maximum extents of the geometry.';
			
COMMENT ON FUNCTION Box3D(geometry ) IS 'args: geomA - Returns a BOX3D representing the maximum extents of the geometry.';
			
COMMENT ON FUNCTION ST_EstimatedExtent(text , text , text ) IS 'args: schema_name, table_name, geocolumn_name - Return the estimated extent of the given spatial table. The estimated is taken from the geometry columns statistics. The current schema will be used if not specified.';
			
COMMENT ON FUNCTION ST_EstimatedExtent(text , text ) IS 'args: table_name, geocolumn_name - Return the estimated extent of the given spatial table. The estimated is taken from the geometry columns statistics. The current schema will be used if not specified.';
			
COMMENT ON FUNCTION ST_Expand(geometry , float) IS 'args: g1, units_to_expand - Returns bounding box expanded in all directions from the bounding box of the input geometry. Uses double-precision';
			
COMMENT ON FUNCTION ST_Expand(box2d , float) IS 'args: g1, units_to_expand - Returns bounding box expanded in all directions from the bounding box of the input geometry. Uses double-precision';
			
COMMENT ON FUNCTION ST_Expand(box3d , float) IS 'args: g1, units_to_expand - Returns bounding box expanded in all directions from the bounding box of the input geometry. Uses double-precision';
			
COMMENT ON AGGREGATE ST_Extent(geometry) IS 'args: geomfield - an aggregate function that returns the bounding box that bounds rows of geometries.';
			
COMMENT ON AGGREGATE ST_3DExtent(geometry) IS 'args: geomfield - an aggregate function that returns the box3D bounding box that bounds rows of geometries.';
			
COMMENT ON FUNCTION Find_SRID(varchar , varchar , varchar ) IS 'args: a_schema_name, a_table_name, a_geomfield_name - The syntax is find_srid(a_db_schema, a_table, a_column) and the function returns the integer SRID of the specified column by searching through the GEOMETRY_COLUMNS table.';
			
COMMENT ON FUNCTION ST_Mem_Size(geometry ) IS 'args: geomA - Returns the amount of space (in bytes) the geometry takes.';
			
COMMENT ON FUNCTION ST_Point_Inside_Circle(geometry , float , float , float ) IS 'args: a_point, center_x, center_y, radius - Is the point geometry insert circle defined by center_x, center_y, radius';
			
COMMENT ON FUNCTION PostGIS_AddBBox(geometry ) IS 'args: geomA - Add bounding box to the geometry.';
			
COMMENT ON FUNCTION PostGIS_DropBBox(geometry ) IS 'args: geomA - Drop the bounding box cache from the geometry.';
			
COMMENT ON FUNCTION PostGIS_HasBBox(geometry ) IS 'args: geomA - Returns TRUE if the bbox of this geometry is cached, FALSE otherwise.';
			