param solutionLocation string

param cosmosAccountName string
// var databaseName = 'ContentProcess'
// var collectionNameProcess = 'Processes'
// var collectionNameSchema = 'Schemas'

// var containers = [
//   {
//     name: collectionNameProcess
//     id: collectionNameProcess
//     partitionKey: '/userId'
//   }
//   {
//     name: collectionNameSchema
//     id: collectionNameSchema
//     partitionKey: '/userId'
//   }
// ]

@allowed(['GlobalDocumentDB', 'MongoDB', 'Parse'])
param kind string = 'GlobalDocumentDB'

param tags object = {}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' = {
  name: cosmosAccountName
  kind: kind
  location: solutionLocation
  tags: tags
  properties: {
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    locations: [
      {
        locationName: solutionLocation
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    apiProperties: (kind == 'MongoDB') ? { serverVersion: '7.0' } : {}
    capabilities: kind == 'MongoDB' ? [{ name: 'EnableMongo' }] : [{ name: 'EnableServerless' }]
    capacityMode: 'Serverless'
    enableFreeTier: false
  }
}

// resource database 'Microsoft.DocumentDB/databaseAccounts/mongodbDatabases@2024-12-01-preview' = {
//   parent: cosmos
//   name: databaseName
//   properties: {
//     resource: { id: databaseName }
//   }

//   resource list 'collections' = [for container in containers: {
//     name: container.name
//     properties: {
//       resource: {
//         id: container.id
//       }
//       options: {}
//     }
//   }]
// }

output cosmosAccountName string = cosmos.name
// output cosmosDatabaseName string = databaseName
