// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Ambient type declarations for non-TypeScript asset imports and
 * third-party modules that lack type definitions.
 */

declare module "*.svg" {
    const content: string;
    export default content;
}

declare module "*.scss";

declare module "*.css";

declare module "react-tiff";
