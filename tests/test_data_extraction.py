from energy_optimizer import ResourceConstraints, ResourceDataExtractor


class TestResourceDataExtractor:
    """Tests for ResourceDataExtractor class"""

    def test_basic_extraction(self, minimal_input_data):
        """Test basic data extraction from minimal input"""
        extractor = ResourceDataExtractor(minimal_input_data)
        constraints = extractor.extract()

        assert isinstance(constraints, ResourceConstraints)
        assert len(constraints.assets) == 1
        assert "test-battery-1" in constraints.assets

    def test_asset_properties_extraction(self, minimal_input_data):
        """Test extraction of asset properties"""
        extractor = ResourceDataExtractor(minimal_input_data)
        constraints = extractor.extract()

        asset_id = "test-battery-1"
        assert constraints.capacity[asset_id] == 100.0
        assert constraints.asset_type[asset_id] == "BT"
        assert constraints.fr_percent[asset_id] == 0.5
        assert constraints.kwh_limits[asset_id] == -500.0

    def test_multi_asset_extraction(self, multi_asset_input_data):
        """Test extraction with multiple assets"""
        extractor = ResourceDataExtractor(multi_asset_input_data)
        constraints = extractor.extract()

        assert len(constraints.assets) == 2
        assert "battery-1" in constraints.assets
        assert "generator-1" in constraints.assets

        assert constraints.asset_type["battery-1"] == "BT"
        assert constraints.asset_type["generator-1"] == "GN"
        assert constraints.capacity["battery-1"] == 100.0
        assert constraints.capacity["generator-1"] == 150.0

    def test_program_extraction(self, minimal_input_data):
        """Test extraction of program types"""
        extractor = ResourceDataExtractor(minimal_input_data)
        constraints = extractor.extract()

        assert "econ" in constraints.programs
        assert "fr" in constraints.programs

    def test_benefit_mapping(self, minimal_input_data):
        """Test benefit values are correctly mapped"""
        extractor = ResourceDataExtractor(minimal_input_data)
        constraints = extractor.extract()

        asset_program = "test-battery-1_econ"
        assert asset_program in constraints.asset_programs

        # Check that benefits exist for this asset_program
        benefit_keys = [k for k in constraints.benefits if k[0] == asset_program]
        assert len(benefit_keys) > 0

    def test_periods_count(self, minimal_input_data):
        """Test that periods count is extracted"""
        extractor = ResourceDataExtractor(minimal_input_data)
        constraints = extractor.extract()

        assert constraints.periods_count == 1

    def test_time_periods_extracted(self, minimal_input_data):
        """Test that time periods are extracted"""
        extractor = ResourceDataExtractor(minimal_input_data)
        constraints = extractor.extract()

        # Should have NO_HOUR_VALUE plus actual hours
        assert len(constraints.time_periods) > 1
        assert "0_0" in constraints.time_periods  # NO_HOUR_VALUE

    def test_usage_limits_calculated(self, minimal_input_data):
        """Test usage limits are calculated"""
        extractor = ResourceDataExtractor(minimal_input_data)
        constraints = extractor.extract()

        asset_id = "test-battery-1"
        assert asset_id in constraints.usage_limits
        # For battery: usage_limit = abs(kwh_limit / capacity) = abs(-500 / 100) = 5
        assert constraints.usage_limits[asset_id] == 5.0

    def test_datetime_mappings_exist(self, minimal_input_data):
        """Test datetime to period mappings exist"""
        extractor = ResourceDataExtractor(minimal_input_data)
        constraints = extractor.extract()

        assert len(constraints.datetime_list) > 0
        assert len(constraints.datetime_to_period) > 0

    def test_econ_fr_mutual_exclusivity_detected(self, minimal_input_data):
        """Test that ECON/FR mutual exclusivity is detected"""
        extractor = ResourceDataExtractor(minimal_input_data)
        constraints = extractor.extract()

        asset_id = "test-battery-1"
        assert asset_id in constraints.econ_fr_enabled
        assert constraints.econ_fr_enabled[asset_id] is True

    def test_dcm_data_extraction(self, dcm_input_data):
        """Test DCM data extraction"""
        extractor = ResourceDataExtractor(dcm_input_data)
        constraints = extractor.extract()

        assert constraints.site_dcm_enabled is True
        assert "dcm" in constraints.programs

    def test_multi_period_extraction(self):
        """Test extraction with multiple periods"""
        data = {
            "ExcludeFirstDcmMonth": False,
            "Resources": [{
                "ResourceId": "test-1",
                "Capacity": 100.0,
                "FrPercent": 0.0,
                "Type": "BT",
                "HourLimit": 0,
                "FirstPeriodHourLimit": None,
                "KwhLimit": -500.0,
                "FuelCost": 0.0,
                "BtEfficiency": 1.0,
                "BtECost": 0.0,
                "ProgramAnnualBenefits": {
                    "econ": {"MonthBenefits": [
                        {"HourBenefits": [{"Hour": 1, "Benefit": 10.0, "DateTime": "01/01/2023 00:00:00"}]},
                        {"HourBenefits": [{"Hour": 1, "Benefit": 12.0, "DateTime": "02/01/2023 00:00:00"}]}
                    ]}
                }
            }],
            "MonthlyLoads": [
                {"Loads": [{"Hour": 1, "Kw": 50.0, "UtilityRate": 0.1, "DcmChargeRate": 0.0, "EconLoadKw": 50.0, "DateTime": "2023-01-01T00:00:00"}]},
                {"Loads": [{"Hour": 1, "Kw": 55.0, "UtilityRate": 0.1, "DcmChargeRate": 0.0, "EconLoadKw": 55.0, "DateTime": "2023-02-01T00:00:00"}]}
            ],
            "DcmData": [[], []]
        }

        extractor = ResourceDataExtractor(data)
        constraints = extractor.extract()

        assert constraints.periods_count == 2
