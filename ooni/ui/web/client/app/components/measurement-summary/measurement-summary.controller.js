MeasurementSummaryController.$inject = ['$stateParams', '$scope', '$http', '$window'];
function MeasurementSummaryController($stateParams, $scope, $http) {
   $http.get('/api/measurement/'+$stateParams.measurementId)
    .then(function(response){
      $scope.measurements = response.data;
    }, function(error){
      console.log(error);
    });
 
}

module.exports = MeasurementSummaryController;
