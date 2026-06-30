// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Type definitions for the SchemaDropdown component and its data sources.
 */

/** A key-value pair used to populate dropdown options. */
export interface OptionList {
    /** Unique schema identifier. */
    readonly key: string;
    /** Human-readable schema name. */
    readonly value: string;
}

/** A schema item as returned by the API. */
export interface SchemaItem {
    /** Unique identifier for the schema. */
    readonly Id: string;
    /** Description of the schema. */
    readonly Description: string;
    /** Display name of the schema. */
    readonly Name: string;
}

/** Shape of the schema-related store slice. */
export interface StoreState {
    /** Available schemas. */
    readonly schemaData: SchemaItem[];
    /** Available schema sets. */
    readonly schemaSetData: SchemaItem[];
    /** Currently selected schema option. */
    readonly schemaSelectedOption: { optionText: string } | null;
    /** Whether schema data is loading. */
    readonly schemaLoader: boolean;
    /** Error message from schema fetch, if any. */
    readonly schemaError: string | null;
}
