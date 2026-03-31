// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for leftPanelSlice — synchronous reducers and async thunk
 * extra-reducer transitions for schema, grid, file, and claim operations.
 */

import reducer, {
    setSchemaSelectedOption,
    setSelectedGridRow,
    setSelectedClaim,
    setRefreshGrid,
    fetchSchemasetData,
    fetchContentTableData,
    fetchSwaggerData,
    deleteProcessedFile,
    deleteClaim,
    createBatch,
    uploadFile,
    submitBatchClaim,
} from './leftPanelSlice';
import type { LeftPanelState, CreateBatchResponse } from './leftPanelSlice';

// ── Helpers ────────────────────────────────────────────────────────────

const gridDefault = {
    total_count: 0,
    total_pages: 0,
    current_page: 1,
    page_size: 500,
    items: [],
};

const getInitialState = (): LeftPanelState => ({
    schemaData: [],
    schemaSetData: [],
    schemaSelectedOption: {},
    schemaLoader: false,
    schemaError: null,
    gridData: { ...gridDefault },
    gridLoader: false,
    processId: null,
    selectedItem: {},
    selectedClaim: null,
    selectionType: null,
    isGridRefresh: false,
    pageSize: 500,
    deleteFilesLoader: [],
    deleteClaimsLoader: [],
    swaggerJSON: null,
});

// ── Initial State ──────────────────────────────────────────────────────

describe('leftPanelSlice', () => {
    describe('initial state', () => {
        it('should return the correct initial state', () => {
            expect(reducer(undefined, { type: 'unknown' })).toEqual(getInitialState());
        });
    });

    // ── Synchronous Reducers ─────────────────────────────────────────────

    describe('setSchemaSelectedOption', () => {
        it('should update the selected schema option', () => {
            const option = { id: 'schema-1', name: 'Test Schema' };
            const state = reducer(getInitialState(), setSchemaSelectedOption(option));
            expect(state.schemaSelectedOption).toEqual(option);
        });
    });

    describe('setSelectedGridRow', () => {
        it('should set processId, selectedItem, and default selectionType to document', () => {
            const item = { process_id: 'p-1', filename: 'test.pdf' };
            const state = reducer(
                getInitialState(),
                setSelectedGridRow({ processId: 'p-1', item })
            );
            expect(state.processId).toBe('p-1');
            expect(state.selectedItem).toEqual(item);
            expect(state.selectionType).toBe('document');
        });

        it('should use the provided selectionType when given', () => {
            const item = { claim_id: 'c-1' };
            const state = reducer(
                getInitialState(),
                setSelectedGridRow({ processId: null, item, selectionType: 'claim' })
            );
            expect(state.selectionType).toBe('claim');
        });
    });

    describe('setSelectedClaim', () => {
        it('should set selectedClaim and clear processId/selectedItem', () => {
            const withSelected: LeftPanelState = {
                ...getInitialState(),
                processId: 'p-1',
                selectedItem: { filename: 'old.pdf' },
            };
            const claim = { claim_id: 'c-1', status: 'approved' };
            const state = reducer(withSelected, setSelectedClaim({ claim }));

            expect(state.selectedClaim).toEqual(claim);
            expect(state.selectionType).toBe('claim');
            expect(state.processId).toBeNull();
            expect(state.selectedItem).toEqual({});
        });
    });

    describe('setRefreshGrid', () => {
        it('should toggle the grid refresh flag', () => {
            const state = reducer(getInitialState(), setRefreshGrid(true));
            expect(state.isGridRefresh).toBe(true);

            const state2 = reducer(state, setRefreshGrid(false));
            expect(state2.isGridRefresh).toBe(false);
        });
    });

    // ── fetchSwaggerData extra-reducers ──────────────────────────────────

    describe('fetchSwaggerData', () => {
        it('should clear swaggerJSON on pending', () => {
            const state: LeftPanelState = {
                ...getInitialState(),
                swaggerJSON: { info: { title: 'Old' } },
            };
            const next = reducer(state, fetchSwaggerData.pending('', undefined));
            expect(next.swaggerJSON).toBeNull();
        });

        it('should set swaggerJSON on fulfilled', () => {
            const payload = { info: { title: 'API' } };
            const next = reducer(
                getInitialState(),
                fetchSwaggerData.fulfilled(payload, '', undefined)
            );
            expect(next.swaggerJSON).toEqual(payload);
        });

        it('should clear swaggerJSON on rejected', () => {
            const state: LeftPanelState = {
                ...getInitialState(),
                swaggerJSON: { info: { title: 'Old' } },
            };
            const next = reducer(
                state,
                fetchSwaggerData.rejected(new Error('fail'), '', undefined)
            );
            expect(next.swaggerJSON).toBeNull();
        });
    });

    // ── fetchSchemasetData ───────────────────────────────

    describe('fetchSchemasetData', () => {
        it('should set schemaLoader on pending', () => {
            const next = reducer(
                getInitialState(),
                fetchSchemasetData.pending('', undefined)
            );
            expect(next.schemaLoader).toBe(true);
            expect(next.schemaError).toBeNull();
        });

        it('should populate schemaSetData on fulfilled', () => {
            const payload = [{ id: '1', name: 'Schema Set A' }];
            const next = reducer(
                getInitialState(),
                fetchSchemasetData.fulfilled(payload, '', undefined)
            );
            expect(next.schemaSetData).toEqual(payload);
            expect(next.schemaLoader).toBe(false);
        });

        it('should set schemaError on rejected', () => {
            const next = reducer(
                getInitialState(),
                fetchSchemasetData.rejected(
                    new Error('Network error'),
                    '',
                    undefined
                )
            );
            expect(next.schemaError).toBe('Network error');
            expect(next.schemaLoader).toBe(false);
        });
    });

    // ── fetchContentTableData extra-reducers ─────────────────────────────

    describe('fetchContentTableData', () => {
        it('should set gridLoader on pending', () => {
            const next = reducer(
                getInitialState(),
                fetchContentTableData.pending('', { pageSize: 10, pageNumber: 1 })
            );
            expect(next.gridLoader).toBe(true);
        });

        it('should populate gridData on fulfilled', () => {
            const payload = {
                total_count: 5,
                total_pages: 1,
                current_page: 1,
                page_size: 10,
                items: [{ id: '1' }],
            };
            const next = reducer(
                getInitialState(),
                fetchContentTableData.fulfilled(payload, '', { pageSize: 10, pageNumber: 1 })
            );
            expect(next.gridData).toEqual(payload);
            expect(next.gridLoader).toBe(false);
        });

        it('should reset gridLoader on rejected', () => {
            const loading: LeftPanelState = { ...getInitialState(), gridLoader: true };
            const next = reducer(
                loading,
                fetchContentTableData.rejected(
                    new Error('fail'),
                    '',
                    { pageSize: 10, pageNumber: 1 }
                )
            );
            expect(next.gridLoader).toBe(false);
        });
    });

    // ── deleteProcessedFile extra-reducers ───────────────────────────────

    describe('deleteProcessedFile', () => {
        it('should add processId to deleteFilesLoader on pending', () => {
            const next = reducer(
                getInitialState(),
                deleteProcessedFile.pending('', { processId: 'p-1' })
            );
            expect(next.deleteFilesLoader).toContain('p-1');
        });

        it('should not push null processId to deleteFilesLoader on pending', () => {
            const next = reducer(
                getInitialState(),
                deleteProcessedFile.pending('', { processId: null })
            );
            expect(next.deleteFilesLoader).toEqual([]);
        });

        it('should remove processId from deleteFilesLoader on fulfilled', () => {
            const state: LeftPanelState = {
                ...getInitialState(),
                deleteFilesLoader: ['p-1'],
            };
            const payload = { process_id: 'p-1', status: 'Success', message: '' };
            const next = reducer(
                state,
                deleteProcessedFile.fulfilled(payload, '', { processId: 'p-1' })
            );
            expect(next.deleteFilesLoader).not.toContain('p-1');
        });

        it('should set isGridRefresh on successful delete', () => {
            const payload = { process_id: 'p-1', status: 'Success', message: '' };
            const next = reducer(
                getInitialState(),
                deleteProcessedFile.fulfilled(payload, '', { processId: 'p-1' })
            );
            expect(next.isGridRefresh).toBe(true);
        });

        it('should remove processId from deleteFilesLoader on rejected', () => {
            const state: LeftPanelState = {
                ...getInitialState(),
                deleteFilesLoader: ['p-1'],
            };
            const next = reducer(
                state,
                deleteProcessedFile.rejected(new Error('fail'), '', { processId: 'p-1' })
            );
            expect(next.deleteFilesLoader).not.toContain('p-1');
        });
    });

    // ── deleteClaim extra-reducers ───────────────────────────────────────

    describe('deleteClaim', () => {
        it('should add claimId to deleteClaimsLoader on pending', () => {
            const next = reducer(
                getInitialState(),
                deleteClaim.pending('', { claimId: 'c-1' })
            );
            expect(next.deleteClaimsLoader).toContain('c-1');
        });

        it('should remove claimId from deleteClaimsLoader on fulfilled', () => {
            const state: LeftPanelState = {
                ...getInitialState(),
                deleteClaimsLoader: ['c-1'],
            };
            const payload = { process_id: 'c-1', status: 'Success', message: '' };
            const next = reducer(
                state,
                deleteClaim.fulfilled(payload, '', { claimId: 'c-1' })
            );
            expect(next.deleteClaimsLoader).not.toContain('c-1');
        });

        it('should set isGridRefresh on successful claim delete', () => {
            const payload = { process_id: 'c-1', status: 'Success', message: '' };
            const next = reducer(
                getInitialState(),
                deleteClaim.fulfilled(payload, '', { claimId: 'c-1' })
            );
            expect(next.isGridRefresh).toBe(true);
        });

        it('should remove claimId from deleteClaimsLoader on rejected', () => {
            const state: LeftPanelState = {
                ...getInitialState(),
                deleteClaimsLoader: ['c-1'],
            };
            const next = reducer(
                state,
                deleteClaim.rejected(new Error('fail'), '', { claimId: 'c-1' })
            );
            expect(next.deleteClaimsLoader).not.toContain('c-1');
        });
    });

    // ── createBatch extra-reducers ────────────────────────────────────────

    describe('createBatch', () => {
        it('should not crash on pending/fulfilled/rejected (no state mutations)', () => {
            const args = { schemaCollectionId: 'collection-1' };
            const payload: CreateBatchResponse = { claim_id: 'claim-1' };

            expect(() =>
                reducer(getInitialState(), createBatch.pending('', args))
            ).not.toThrow();
            expect(() =>
                reducer(getInitialState(), createBatch.fulfilled(payload, '', args))
            ).not.toThrow();
            expect(() =>
                reducer(getInitialState(), createBatch.rejected(new Error('fail'), '', args))
            ).not.toThrow();
        });
    });

    // ── uploadFile extra-reducers ────────────────────────────────────────

    describe('uploadFile', () => {
        it('should not crash on pending/fulfilled/rejected (no state mutations)', () => {
            const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
            const args = { file, claimId: 'claim-1', schemaId: 'schema-1' };

            // These are no-op handlers, just verify they don't throw
            expect(() =>
                reducer(getInitialState(), uploadFile.pending('', args))
            ).not.toThrow();
            expect(() =>
                reducer(getInitialState(), uploadFile.fulfilled({}, '', args))
            ).not.toThrow();
            expect(() =>
                reducer(getInitialState(), uploadFile.rejected(new Error('fail'), '', args))
            ).not.toThrow();
        });
    });

    // ── submitBatchClaim extra-reducers ───────────────────────────────────

    describe('submitBatchClaim', () => {
        it('should not crash on pending/fulfilled/rejected (no state mutations)', () => {
            const args = { claimProcessId: 'claim-1' };

            expect(() =>
                reducer(getInitialState(), submitBatchClaim.pending('', args))
            ).not.toThrow();
            expect(() =>
                reducer(getInitialState(), submitBatchClaim.fulfilled({}, '', args))
            ).not.toThrow();
            expect(() =>
                reducer(getInitialState(), submitBatchClaim.rejected(new Error('fail'), '', args))
            ).not.toThrow();
        });
    });
});
