from . import cadasters_population, facilities

if __name__ == "__main__":
    print("cadasters/population:", cadasters_population.run())
    print("facilities/travel_time:", facilities.run())
